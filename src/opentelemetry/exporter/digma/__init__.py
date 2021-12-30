import logging
import os

from opentelemetry.proto.common.v1.common_pb2 import KeyValue
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Span
from typing import Sequence

from .v1.digma_pb2 import ExportRequest, ErrorFrame, ErrorEvent

from .v1.digma_pb2_grpc import DigmaCollectorStub

from opentelemetry.exporter.digma.traceback_parser import TracebackParser, TracebackFrame
from opentelemetry.proto.trace.v1.trace_pb2 import Span as proto_span
from opentelemetry.sdk.trace import Event, Span
from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue

logger = logging.getLogger(__name__)

import grpc


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

    def export(self, spans: Sequence[Span]) -> SpanExportResult:

        export_request = None
        spans_infos = []
        for span in spans:
            error_events = []
            events = []
            for span_event in span.events:
                if span_event.name == 'exception':
                    stack_trace = span_event.attributes['exception.stacktrace']
                    error_frames = TracebackParser().error_flow_parser(stack_trace)
                    exception_type = span_event.attributes['exception.type']
                    name = f"{exception_type} from {error_frames[-1].func_name}"
                    error_event = ErrorEvent(exception_message=span_event.attributes['exception.message'],
                                             exception_type=span_event.attributes['exception.type'],
                                             exception_stack=stack_trace,
                                             name=name,
                                             timestamp=str(span_event.timestamp),
                                             frames=[ErrorFrame(module_name=ef.func_name,
                                                                module_path=ef.path,
                                                                excuted_code=ef.line,
                                                                line_number=ef.line_num) for ef in error_frames])
                    error_events.append(error_event)
                    events.append(self._create_proto_event(span_event))

            spans_infos.append(
                ExportRequest.SpanInformation(span_id=str(span.context.span_id),
                                              trace_id=str(span.context.trace_id),
                                              error_events=error_events,
                                              events=events))

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
