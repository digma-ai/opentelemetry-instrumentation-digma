import logging
from opentelemetry.sdk.resources import SERVICE_NAME
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Span
from typing import Sequence
from opentelemetry.trace.span import SpanContext
logger = logging.getLogger(__name__)
from .collector_pb2 import ExportRequest
from .collector_pb2_grpc import DigmaCollectorStub
import grpc

class DigmaExporter(SpanExporter):

    def __init__(self) -> None:
        self._closed = False
        super().__init__()

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        
        export_request = None

        for span in spans:
            exceptions = []
            export_request =ExportRequest(span_id=str(span.context.span_id),
                          trace_id= str(span.context.trace_id),
                          service_name=span.resource.attributes['service.name'],
                          errors=exceptions)
            for span_event in span.events:
                if span_event.name == 'exception':
                    error_info = ExportRequest.ErrorInformation(
                        exception_name=span_event.attributes['exception.message'],
                        exception_type=span_event.attributes['exception.type'],
                        exception_stack=span_event.attributes['exception.stacktrace'],
                        timestamp=str(span_event.timestamp))
                    exceptions.append(error_info)

        if self._closed:
            logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE

        with grpc.insecure_channel('localhost:5000') as channel:
            stub = DigmaCollectorStub(channel)
            response =  stub.Export(export_request)
            print("Greeter client received: " + response.message)

    def shutdown(self) -> None:
        self._closed = True
