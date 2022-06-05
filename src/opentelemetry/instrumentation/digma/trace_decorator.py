import inspect
import sys
import types
from functools import wraps
from typing import Callable, Dict

from opentelemetry.trace import Tracer

from opentelemetry import trace
from inspect import getmembers, isfunction


class TracingDecoratorOptions:
    class NamingSchemes:
        @staticmethod
        def function_qualified_name(func: Callable):
            return func.__qualname__

        default_scheme = function_qualified_name

    naming_scheme: Callable[[Callable], str] = NamingSchemes.default_scheme
    default_attributes: Dict[str, str] = {}

    @staticmethod
    def set_naming_scheme(naming_scheme: Callable[[Callable], str]):
        TracingDecoratorOptions.naming_scheme = naming_scheme

    @staticmethod
    def set_default_attributes(attributes: Dict[str, str] = None):
        for att in attributes:
            TracingDecoratorOptions.default_attributes[att] = attributes[att]


def instrument_class(record_exception: bool = True,
                     attributes: Dict[str, str] = None,
                     include_private=False):
    def decorate_class(cls):
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            if not name.startswith('_') or include_private:
                setattr(cls, name, instrument(record_exception=record_exception,
                                              attributes=attributes)(method))
        return cls
    return decorate_class


class TraceDecoratorLogic:
    @staticmethod
    def wrap_function_with_span( func, tracer, span_name,record_exception, attributes, *args, **kwargs):
        name = span_name or TracingDecoratorOptions.naming_scheme(func)
        with tracer.start_as_current_span(name, record_exception=record_exception) as span:
            TraceDecoratorLogic._set_attributes(span, TracingDecoratorOptions.default_attributes)
            TraceDecoratorLogic._set_attributes(span, attributes)
            return func(*args, **kwargs)

    @staticmethod
    def _set_attributes(span, attributes_dict):
        if attributes_dict:
            for att in attributes_dict:
                span.set_attribute(att, attributes_dict[att])


def instrument(span_name: str = "", record_exception: bool = True,
               attributes: Dict[str, str] = None, existing_tracer: Tracer = None):

    def span_decorator(func):
        tracer = existing_tracer or trace.get_tracer(func.__module__)

        def _set_attributes(span, attributes_dict):
            if attributes_dict:
                for att in attributes_dict:
                    span.set_attribute(att, attributes_dict[att])

        undecorated_func = getattr(func, '__wrapped__', None)
        if undecorated_func:
            # We have already decorated this function, override
            return func


        @wraps(func)
        def wrap_with_span(*args, **kwargs):
            name = span_name or TracingDecoratorOptions.naming_scheme(func)
            with tracer.start_as_current_span(name, record_exception=record_exception) as span:
                _set_attributes(span, TracingDecoratorOptions.default_attributes)
                _set_attributes(span, attributes)
                return func(*args, **kwargs)

        return wrap_with_span

    return span_decorator
