import logging
import os
import typing

import grpc
from anytree import PreOrderIter
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import SpanKind

import opentelemetry.exporter.digma.common as common
from opentelemetry.exporter.digma.instrumnetation_tools import extend_otel_expansion_recording
from opentelemetry.exporter.digma.proto_conversions import _create_proto_event
from opentelemetry.exporter.digma.traceback_parser import TracebackParser
from .proto_conversions import _convert_span_kind, _create_proto_link, _convert_status_code, _create_proto_status, \
    _create_proto_span
from .v1.digma_pb2 import ExportRequest, ErrorFrame, ErrorEvent, ErrorFrameStack
from .v1.digma_pb2_grpc import DigmaCollectorStub

logger = logging.getLogger(__name__)

extend_otel_expansion_recording()


# Span.add_event = add_event

class DigmaExporter(SpanExporter):

    def __init__(self) -> None:
        self._closed = False
        super().__init__()

    @staticmethod
    def _generate_error_flow_name(exception_type: str, error_frame_stack: ErrorFrameStack):
        return f"{exception_type} from {error_frame_stack.frames[-1].module_name}"

    @staticmethod
    def _forward_slash_for_paths(file_path: str) -> str:
        return file_path.replace('\\', '/')

    def export(self, spans: typing.Sequence[Span]) -> SpanExportResult:

        spans_infos = self._extract_span_infos(spans)

        if not spans_infos:  # no error event, no export needed
            return SpanExportResult.SUCCESS

        errors_info = self._extract_error_events(spans)

        proto_span_infos = [_create_proto_span(span) for span in spans]

        export_request = ExportRequest(
            environment=os.environ.get('ENVIRONMENT', ''),
            commit_id=os.environ.get('GIT_COMMIT_ID', ''),
            programming_language='python',
            error_information=errors_info,
            spans=spans_infos,
            spans_infos=proto_span_infos
        )
        if self._closed:
            logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE

        with grpc.insecure_channel('localhost:5050') as channel:
            stub = DigmaCollectorStub(channel)
            response = stub.Export(export_request)
            print("Greeter client received: " + response.message)

    # Legacy - need to remove
    def _extract_span_infos(self, spans):
        spans_infos = []
        for span in spans:
            error_events = []
            events = []
            for span_event in span.events:
                if span_event.name == 'exception':
                    full_stack_trace = span_event.attributes['exception.stacktrace.full']
                    stack_trace = span_event.attributes['exception.stacktrace']
                    stacks = TracebackParser.parse_error_flow_stacks(full_stack_trace)
                    exception_type = span_event.attributes['exception.type']
                    error_event = ErrorEvent(exception_message=span_event.attributes['exception.message'],
                                             exception_type=span_event.attributes['exception.type'],
                                             exception_stack=stack_trace,
                                             name=self._generate_error_flow_name(exception_type, stacks[0]),
                                             timestamp=str(span_event.timestamp),
                                             stacks=stacks)
                    error_events.append(error_event)
                    events.append(_create_proto_event(span_event))

            if error_events:
                spans_infos.append(
                    ExportRequest.SpanInformation(span_id=str(span.context.span_id),
                                                  trace_id=str(span.context.trace_id),
                                                  error_events=error_events,
                                                  events=events))
        return spans_infos

    def _extract_error_events(self, spans: typing.Sequence[Span]):
        spans_by_id = {span.context.span_id: span for span in spans}
        roots = common.create_span_hierarchy(spans)
        error_events = []
        for root in roots:
            # List of unique path events, events contained in these events will not be recorded separately
            span_path_events = []
            for node in PreOrderIter(root):
                current_span = spans_by_id[node.name]
                events = []
                for span_event in current_span.events:
                    if span_event.name == 'exception':
                        stack_trace = span_event.attributes['exception.stacktrace']
                        full_stack_trace = span_event.attributes['exception.stacktrace.full']

                        # We omit the otel stack from recording the exception because they are an artifact
                        stacks = TracebackParser \
                            .parse_error_flow_stacks(full_stack_trace, str(current_span.context.span_id),
                                                     ignore_list=['opentelemetry/trace/__init__.py',
                                                                  'opentelemetry/sdk/trace/__init__.py'])
                        exception_already_captured = False
                        for existing_event in span_path_events:
                            contained_frames = common.get_contained_frames(stacks, existing_event.stacks)

                            # If all he frames are fully captured in the existing stack we don't record
                            # as separate event but still mark them with the span id of this stack
                            if len(contained_frames) == common.frame_count(stacks):
                                exception_already_captured = True
                                for frame in contained_frames:
                                    frame.span_id = str(current_span.context.span_id)

                        if not exception_already_captured:
                            exception_type = span_event.attributes['exception.type']
                            error_event = ErrorEvent(exception_message=span_event.attributes['exception.message'],
                                                     exception_type=span_event.attributes['exception.type'],
                                                     exception_stack=stack_trace,
                                                     name=self._generate_error_flow_name(exception_type, stacks[0]),
                                                     timestamp=str(span_event.timestamp),
                                                     stacks=stacks)
                            events.append(_create_proto_event(span_event))

                            span_path_events.append(error_event)

            error_events += span_path_events

        for event in error_events:
            event.handled = True
            print("---error---" + event.name)
            for stack in event.stacks:
                for frame in stack.frames:
                    if event.handled and spans_by_id[int(frame.span_id)].kind == SpanKind.SERVER:
                        event.handled = False
                    print(f"#{frame.span_id} - {frame.module_path}/{frame.module_name}:{frame.line_number}")

        return ExportRequest.ErrorsInformation(error_events=error_events)

    def shutdown(self) -> None:
        self._closed = True
