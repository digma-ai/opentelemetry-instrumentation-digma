import logging
import os
import traceback
import grpc
from typing import Sequence, List, Iterator

from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue
from opentelemetry.proto.trace.v1.trace_pb2 import Span as proto_span
from opentelemetry.sdk.trace import Event, Span
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from opentelemetry.exporter.digma.traceback_parser import TracebackParser, TracebackFrameStack
from .v1.digma_pb2 import ExportRequest, ErrorFrame, ErrorEvent, ErrorFrameStack
from .v1.digma_pb2_grpc import DigmaCollectorStub
import sys
import traceback
from opentelemetry.util import types
from typing import Optional
import opentelemetry.exporter.digma.common as common

logger = logging.getLogger(__name__)
    
default_add_event = Span.add_event
default_record_exception = Span.record_exception


def record_exception(
        self,
        exception: Exception,
        attributes: types.Attributes = None,
        timestamp: Optional[int] = None,
        escaped: bool = False,
    ) -> None:
     
    _attributes = {'exception.stacktrace.full': common.get_traceback_with_locals(sys.exc_info()[1])}
    if attributes:
        _attributes.update(attributes)
    return default_record_exception(self,exception, _attributes,timestamp, escaped)
    
Span.record_exception = record_exception
#Span.add_event = add_event

class DigmaExporter(SpanExporter):

    def __init__(self) -> None:
        self._closed = False
        super().__init__()

    def _create_proto_event(self, event: Event) -> proto_span.Event:
        attributes = []
        for attribute in event.attributes:
            attributes.append(KeyValue(key=attribute, value=AnyValue(string_value=event.attributes[attribute])))
        return proto_span.Event(time_unix_nano=event.timestamp,
                                name=event.name,
                                attributes=attributes)

    @staticmethod
    def _generate_error_flow_name(exception_type: str, error_frame_stack: ErrorFrameStack):
        return f"{exception_type} from {error_frame_stack.frames[-1].module_name}"

    @staticmethod
    def _forward_slash_for_paths(file_path: str) -> str:
        return file_path.replace('\\', '/')

    def export(self, spans: Sequence[Span]) -> SpanExportResult:

        export_request = None
        spans_infos = []
        for span in spans:
            error_events = []
            events = []
            for span_event in span.events:
                if span_event.name == 'exception':
                    full_stack_trace = span_event.attributes['exception.stacktrace.full']
                    stack_trace = span_event.attributes['exception.stacktrace']
                    stacks = TracebackParser.parse_error_flow_stacks(stack_trace)
                    exception_type = span_event.attributes['exception.type']
                    error_event = ErrorEvent(exception_message=span_event.attributes['exception.message'],
                                             exception_type=span_event.attributes['exception.type'],
                                             exception_stack=stack_trace,
                                             name=self._generate_error_flow_name(exception_type, stacks[0]),
                                             timestamp=str(span_event.timestamp),
                                             stacks=stacks)
                    error_events.append(error_event)
                    events.append(self._create_proto_event(span_event))
            
            if error_events:
                spans_infos.append(
                    ExportRequest.SpanInformation(span_id=str(span.context.span_id),
                                                  trace_id=str(span.context.trace_id),
                                                  error_events=error_events,
                                                  events=events))
        if not spans_infos:  # no error event, no export needed
            return SpanExportResult.SUCCESS

        export_request = ExportRequest(
            service_name=span.resource.attributes['service.name'],
            environment=os.environ.get('ENVIRONMENT', ''),
            commit_id=os.environ.get('GIT_COMMIT_ID', ''),
            programming_language='python',
            spans=spans_infos
        )
        if self._closed:
            logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE

        with grpc.insecure_channel('localhost:5050') as channel:
            stub = DigmaCollectorStub(channel)
            response = stub.Export(export_request)
            print("Greeter client received: " + response.message)

    def shutdown(self) -> None:
        self._closed = True
