import inspect
from functools import wraps
from typing import Callable, Dict

from opentelemetry.trace import Tracer

from opentelemetry import trace


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


def instrument(_func_or_class=None, *, span_name: str = "", record_exception: bool = True,
               attributes: Dict[str, str] = None, existing_tracer: Tracer = None, ignore=False):
    """
    A decorator to instrument a class or function with an OTEL tracing span.
    :param _func_or_class: The function or span to instrument, this is automatically assigned
    :param span_name: Specify the span name explicitly, rather than use the naming convention.
    This parameter has no effect for class decorators: str
    :param record_exception: Sets whether any exceptions occurring in the span and the stacktrace are recorded
    automatically: bool
    :param attributes:A dictionary of span attributes. These will be automatically added to the span. If defined on a
    class decorator, they will be added to every function span under the class.: dict
    :param existing_tracer: Use a specific tracer instead of creating one :Tracer
    :param ignore: Do not instrument this function, has no effect for class decorators:bool
    :return:The decorator function
    """

    def decorate_class(cls):
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            # Ignore private functions, TODO: maybe make this a setting?
            if not name.startswith('_'):
                setattr(cls, name, instrument(record_exception=record_exception,
                                              attributes=attributes,
                                              existing_tracer=existing_tracer)(method))
        return cls

    # Check if this is a span or class decorator
    if inspect.isclass(_func_or_class):
        return decorate_class(_func_or_class)

    def span_decorator(func_or_class):

        if inspect.isclass(func_or_class):
            return decorate_class(func_or_class)

        # Check if already decorated (happens if both class and function
        # decorated). If so, we keep the function decorator settings only
        undecorated_func = getattr(func_or_class, '__tracing_unwrapped__', None)
        if undecorated_func:
            # We have already decorated this function, override
            return func_or_class

        setattr(func_or_class, '__tracing_unwrapped__', func_or_class)

        tracer = existing_tracer or trace.get_tracer(func_or_class.__module__)

        def _set_attributes(span, attributes_dict):
            if attributes_dict:
                for att in attributes_dict:
                    span.set_attribute(att, attributes_dict[att])

        @wraps(func_or_class)
        def wrap_with_span(*args, **kwargs):
            name = span_name or TracingDecoratorOptions.naming_scheme(func_or_class)
            with tracer.start_as_current_span(name, record_exception=record_exception) as span:
                _set_attributes(span, TracingDecoratorOptions.default_attributes)
                _set_attributes(span, attributes)
                return func_or_class(*args, **kwargs)

        if ignore:
            return func_or_class

        return wrap_with_span

    if _func_or_class is None:
        return span_decorator
    else:
        return span_decorator(_func_or_class)
