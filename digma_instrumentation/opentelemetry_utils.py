from typing import Sequence, Dict, List

from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExportResult

from digma_instrumentation.configuration import Configuration


def opentelemetry_aiohttp_middleware(name: str):
    from aiohttp import web
    tracer = trace.get_tracer(name)
    @web.middleware
    async def middleware(request: web.Request, handler):
        with tracer.start_as_current_span(request.match_info.route.resource.canonical, kind=SpanKind.SERVER):
            return await handler(request)
    return middleware


def opentelemetry_init(service_name: str, digma_conf: Configuration, digma_endpoint: str, test: bool = False):
    resource = Resource.create(attributes={SERVICE_NAME: service_name}).merge(digma_conf.resource)
    if test:
        exporter = OTLPSpanExporterForTests(endpoint=digma_endpoint, insecure=True)
    else:
        exporter = OTLPSpanExporter(endpoint=digma_endpoint, insecure=True)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


class OTLPSpanExporterForTests(OTLPSpanExporter):
    def __init__(self, endpoint: str, insecure: bool):
        super().__init__(endpoint=endpoint, insecure=insecure)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self.update_timestamps(spans)
        return super().export(spans)

    @staticmethod
    def update_timestamps(spans: Sequence[ReadableSpan]):
        traces: Dict[str, List[ReadableSpan]] = {}
        for span in spans:
            trace_id = span.context.trace_id
            traces.setdefault(trace_id, []).append(span)

        for trace_id, trace_spans in traces.items():
            simulated_spans = [span for span in trace_spans if (span.attributes and 'x-simulated-time' in span.attributes)]
            if not simulated_spans:
                continue

            root = simulated_spans[0]
            new_time = int(root.attributes['x-simulated-time'])

            for span in trace_spans:
                delta = span.start_time - root.start_time
                duration = span.end_time - span.start_time

                for event in span.events:
                    delta = event.timestamp - span.start_time
                    event._timestamp = new_time + delta

                span._start_time = new_time + delta
                span._end_time = span.start_time + duration
