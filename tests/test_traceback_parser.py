import traceback
from typing import Optional
from unittest import TestCase

from opentelemetry.exporter.digma import TracebackParser


class TracebackParserTest(TestCase):
    def test_multiple_traceback(self):
        def e():
            raise ValueError("e")

        def b():
            try:
                e()
            except Exception:
                raise ValueError(b)

        def c():
            b()

        def a():
            try:
                c()
            except Exception:
                raise EnvironmentError(a)

        exc_stacktrace: str = Optional[None]
        try:
            a()
        except:
            exc_stacktrace = traceback.format_exc()

        frame_stacks = TracebackParser().parse_error_flow_stacks(stacktrace=exc_stacktrace)
        self.assertEqual(len(frame_stacks), 3)
        # more asserts should be added

    def test_single_traceback(self):
        try:
            raise ValueError('a')
        except:
            exc_stacktrace = traceback.format_exc()

        frame_stacks = TracebackParser().parse_error_flow_stacks(stacktrace=exc_stacktrace)
        self.assertEqual(len(frame_stacks), 1)
