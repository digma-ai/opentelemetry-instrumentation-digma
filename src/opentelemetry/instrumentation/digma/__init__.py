from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry import trace
from opentelemetry.instrumentation.digma.digma_configuration import DigmaConfiguration
from opentelemetry.instrumentation.digma.instrumentation_extensions import extend_otel_exception_recording

extend_otel_exception_recording()


def digma_opentelemetry_boostrap(service_name: str, digma_backend: str, configuration: DigmaConfiguration):
    """
    Quickly sets up Digma with the required parametesr based on the OpenTelemetry resource and parameters
    This function is a quick setup for Digma and OTLP, if you already have OTLP set up you probably don't need it.
    :param service_name: The service name used to identify this service/process
    :param digma_backend: The local or remote Digma backend URL
    :param configuration: Callback to configure additional settings
    :return:
    """
    resource = Resource.create(attributes={SERVICE_NAME: service_name})
    resource = resource.merge(configuration.resource)
    exporter = OTLPSpanExporter(endpoint=digma_backend, insecure=True)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)




