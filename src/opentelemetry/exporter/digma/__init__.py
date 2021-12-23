import logging
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Span
from typing import Sequence


from opentelemetry.exporter.digma.traceback_parser import TracebackParser, TracebackFrame
from opentelemetry.exporter.digma.v1.digma_pb2 import ErrorEvent, ErrorFrame, ExportRequest
from opentelemetry.exporter.digma.v1.digma_pb2_grpc import DigmaCollectorStub

logger = logging.getLogger(__name__)

import grpc


class DigmaExporter(SpanExporter):

    def __init__(self) -> None:
        self._closed = False
        super().__init__()

    def export(self, spans: Sequence[Span]) -> SpanExportResult:

        export_request = None
        spans_infos = []
        for span in spans:
            error_events = []
            for span_event in span.events:
                if span_event.name == 'exception':
                    stack_trace = span_event.attributes['exception.stacktrace']
                    error_frames = TracebackParser().error_flow_parser(stack_trace)
                    error_event = ErrorEvent(frames=[ErrorFrame(module_name=ef.func_name,
                                                                module_path=ef.path,
                                                                excuted_code=ef.line,
                                                                line_number=ef.line_num) for ef in error_frames])
                    error_events.append(error_event)

            spans_infos.append(
                ExportRequest.SpanInformation(span_id=str(span.context.span_id),
                                              trace_id=str(span.context.trace_id),
                                              error_events=error_events))

        export_request = ExportRequest(
            service_name=span.resource.attributes['service.name'],
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
