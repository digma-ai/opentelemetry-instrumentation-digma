
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from digma_instrumentation.configuration import Configuration


def opentelemetry_aiohttp_middleware(name: str):
    from aiohttp import web
    tracer = trace.get_tracer(name)
    @web.middleware
    async def middleware(request: web.Request, handler):
        with tracer.start_as_current_span(request.match_info.route.resource.canonical, kind=SpanKind.SERVER):
            return await handler(request)
    return middleware


def opentelemetry_init(service_name: str, digma_conf: Configuration, digma_endpoint: str):
    resource = Resource.create(attributes={SERVICE_NAME: service_name}).merge(digma_conf.resource)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=digma_endpoint, insecure=True)))
    trace.set_tracer_provider(provider)

