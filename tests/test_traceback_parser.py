import traceback
from typing import Optional
from unittest import TestCase

from opentelemetry.exporter.digma import TracebackParser
import opentelemetry.exporter.digma.common as common
import json
from stubs import ExceptionWithParams


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

    def test_traceback_with_locals(self):
        try:
            ExceptionWithParams().throw_exception("1", "2")
        except Exception as e:
            exc_stacktrace = common.get_traceback_with_locals(e)
        
        frame_stacks = TracebackParser().parse_error_flow_stacks(stacktrace=exc_stacktrace)
        params = json.loads(frame_stacks[0].frames[0].parameters)
        self.assertIn('arg1', params)
        self.assertIn('arg2', params)

        self.assertEqual(params['arg1'], "1")
        self.assertEqual(params['arg2'], "1")

   
        print('g')

    def test_single_traceback(self):
        try:
            raise ValueError('a')
        except:
            exc_stacktrace = traceback.format_exc()

        frame_stacks = TracebackParser().parse_error_flow_stacks(stacktrace=exc_stacktrace)
        self.assertEqual(len(frame_stacks), 1)

    def test_traceback_with_frame_with_no_line(self):
        try:
            print(eval("100/x", {"x": 0}))
        except:
            exc_stacktrace = traceback.format_exc()

        frame_stacks = TracebackParser().parse_error_flow_stacks(stacktrace=exc_stacktrace)
        self.assertEqual(len(frame_stacks), 1)
        self.assertIsNone(frame_stacks[0].frames[1].line)

    # @pytest.mark.parametrize("recursion_depth,expected", [(4, 1), (10, 7)])
    def test_recursion(self):

        def recursion_call(depth: int):
            if depth != 0:
                print(depth)
                return recursion_call(depth - 1)
            else:
                raise ValueError('?')

        recursion_depth = 4
        expected = 1  # check _RECURSIVE_CUTOFF under traceback.py  equals to 3
        try:
            recursion_call(recursion_depth)
        except:
            exc_stacktrace = traceback.format_exc()

        frame_stacks = TracebackParser().parse_error_flow_stacks(stacktrace=exc_stacktrace)

        self.assertEqual(frame_stacks[0].frames[3].repeat, expected)

        recursion_depth = 10
        expected = 7  # check _RECURSIVE_CUTOFF under traceback.py equals to 3
        try:
            recursion_call(recursion_depth)
        except:
            exc_stacktrace = traceback.format_exc()

        frame_stacks = TracebackParser().parse_error_flow_stacks(stacktrace=exc_stacktrace)

        self.assertEqual(frame_stacks[0].frames[3].repeat, expected)  # check
