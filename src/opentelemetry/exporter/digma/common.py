import traceback
from .v1.digma_pb2 import ExportRequest, ErrorFrame, ErrorEvent, ErrorFrameStack
from typing import Sequence, List
from opentelemetry.sdk.trace import Span
from anytree import Node
import os

IGNORE_LIST = [os.path.join('opentelemetry', 'trace', '__init__.py'),
               os.path.join('opentelemetry', 'sdk', 'trace', '__init__.py')]

BUILT_IN_EXCEPTIONS = [
     "SystemExit",  "KeyboardInterrupt", "GeneratorExit", "StopIteration", "StopAsyncIteration", "ArithmeticError",
     "FloatingPointError",  "OverflowError", "ZeroDivisionError", "AssertionError", "AttributeError", "BufferError",
     "EOFError", "ImportError", "ModuleNotFoundError", "LookupError", "IndexError", "KeyError", "MemoryError",
     "NameError", "UnboundLocalError", "BlockingIOError", "ChildProcessError",
      "ConnectionResetError", "FileExistsError",
     "FileNotFoundError", "InterruptedError", "IsADirectoryError", "NotADirectoryError", "PermissionError",
     "ProcessLookupError", "ReferenceError", "RuntimeError", "NotImplementedError", "RecursionError",
     "SyntaxError", "IndentationError", "TabError", "SystemError", "TypeError", "ValueError", "UnicodeError",
     "UnicodeDecodeError", "UnicodeEncodeError", "UnicodeTranslateError"
]


def frame_equals(frame1: ErrorFrame, frame2: ErrorFrame):
    return frame1.module_path == frame2.module_path and \
           frame1.executed_code == frame2.executed_code and \
           frame1.line_number == frame2.line_number and \
           frame1.parameters == frame2.parameters


def is_builtin_exception(exception):
    return exception in BUILT_IN_EXCEPTIONS


def frame_count(stacks):
    count = 0
    for stack in stacks:
        count += len(stack.frames)
    return count


def get_contained_frames(source: ErrorFrameStack, target: ErrorFrameStack):
    contained_frames = []
    for source_stack, target_stack in zip(source, target):
        for source_frame, target_frame in zip(reversed(source_stack.frames),
                                              reversed(target_stack.frames)):
            if frame_equals(source_frame, target_frame):
                contained_frames.append(target_frame)
    return contained_frames


def _get_next_span_level(parents, spans: Sequence[Span]):
    return {span.context.span_id: Node(span.context.span_id, parent=parents[span.parent.span_id])
            for span in spans if span.parent and span.parent.span_id in parents}


def create_span_hierarchy(spans: Sequence[Span]) -> List[Node]:
    root_nodes = {span.context.span_id: Node(span.context.span_id)
                  for span in spans if span.parent is None}
    parent_nodes = root_nodes
    while parent_nodes:
        parent_nodes = _get_next_span_level(parent_nodes, spans)

    return root_nodes.values()

