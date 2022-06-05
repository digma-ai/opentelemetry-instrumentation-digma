from typing import Callable

from opentelemetry.instrumentation.digma.trace_decorator import instrument_class, instrument


@instrument_class()
class A:

    def function_one(self):
        pass

    def function_two(self):
        pass

    def _function_three(self):
        pass


@instrument_class(attributes={"one": "two"})
class B:

    def function_one(self):
        pass

    def function_two(self):
        pass

    def _function_three(self):
        pass


@instrument_class(attributes={"one": "two"})
class C:

    @instrument(span_name="function_decorator", attributes={"two": "three"})
    def function_one(self):
        pass

    def function_two(self):
        pass

    def _function_three(self):
        pass


class ModuleClass:

    def function_one(self):
        pass
