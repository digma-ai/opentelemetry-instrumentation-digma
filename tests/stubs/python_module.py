from typing import Callable

from codetiming import Timer

from opentelemetry.instrumentation.digma.trace_decorator import instrument


@instrument
class A:

    def function_one(self):
        pass

    def function_two(self):
        pass

    def _function_three(self):
        pass


@instrument(attributes={"one": "two"})
class B:

    def function_one(self):
        pass

    @instrument(span_name="function_decorator", attributes={"two": "three"})
    @Timer(name="decorator")
    def function_two(self):
        pass

    def _function_three(self):
        pass


@instrument(attributes={"one": "two"})
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
