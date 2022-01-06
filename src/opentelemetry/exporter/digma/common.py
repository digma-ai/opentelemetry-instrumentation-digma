import traceback
from .v1.digma_pb2 import ExportRequest, ErrorFrame, ErrorEvent, ErrorFrameStack
from typing import Sequence, List
from opentelemetry.sdk.trace import Span
from anytree import Node


def frame_equals(frame1 : ErrorFrame, frame2: ErrorFrame):
    return frame1.module_path == frame2.module_path and \
            frame1.executed_code == frame2.executed_code and \
            frame1.line_number == frame2.line_number and \
            frame1.parameters == frame2.parameters  

def frame_count(stacks):
    count = 0
    for stack in stacks:
        count+=len(stack.frames)
    return count
                                        
def get_contained_frames(source : ErrorFrameStack, target : ErrorFrameStack):
    
    contained_frames = []
    for source_stack, target_stack in zip(source,target):
        for source_frame, target_frame in zip(reversed(source_stack.frames),
                                                reversed(target_stack.frames)):
            if frame_equals(source_frame,target_frame):
                contained_frames.append(target_frame)
    return contained_frames

def get_next_span_level(parents, spans:Sequence[Span]):
    return {span.context.span_id : Node(span.context.span_id, parent=parents[span.parent.span_id]) 
            for span in spans if span.parent and span.parent.span_id in parents}

def create_span_hierarchy(spans: Sequence[Span]) -> List[Node]:        
    root_nodes = {span.context.span_id : Node(span.context.span_id) 
                    for span in spans if span.parent==None }
    parent_nodes = root_nodes
    while parent_nodes:
        parent_nodes = get_next_span_level(parent_nodes,spans)

    return root_nodes.values()

def get_traceback_with_locals(ex: Exception):
    if not ex:
        return None

    st = list(iter(traceback.TracebackException.from_exception(
        ex, limit=None, capture_locals=True).format()))

    full_trace = str.join('\n', st)

    return full_trace
