import logging
from opentelemetry.sdk.resources import SERVICE_NAME
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Span
from typing import Sequence
from opentelemetry.trace.span import SpanContext

logger = logging.getLogger(__name__)
import v1.digma_pb2
import v1.digma_pb2_grpc

import grpc


class DigmaExporter(SpanExporter):

    def __init__(self) -> None:
        self._closed = False
        super().__init__()

    def export(self, spans: Sequence[Span]) -> SpanExportResult:

        export_request = None
        span_info_list = []
        for span in spans:
            errors = []

            for span_event in span.events:
                if span_event.name == 'exception':
                    error_info = ExportRequest.ErrorInformation(
                        exception_name=span_event.attributes['exception.message'],
                        exception_type=span_event.attributes['exception.type'],
                        exception_stack=span_event.attributes['exception.stacktrace'],
                        timestamp=str(span_event.timestamp))
                    errors.append(error_info)

            span_info = ExportRequest.SpanInformation(span_id=str(span.context.span_id),
                                                      trace_id=str(span.context.trace_id),
                                                      service_name=span.resource.attributes['service.name'],
                                                      errors=errors)
            span_info_list.append(span_info)

        export_request = ExportRequest(spans=span_info_list)
        if self._closed:
            logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE

        with grpc.insecure_channel('localhost:5050') as channel:
            stub = DigmaCollectorStub(channel)
            response = stub.Export(export_request)
            print("Greeter client received: " + response.message)

    def shutdown(self) -> None:
        self._closed = True
