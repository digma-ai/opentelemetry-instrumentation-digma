import inspect
import os
from importlib import util

from opentelemetry.attributes import BoundedAttributes
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, DEPLOYMENT_ENVIRONMENT
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from digma_instrumentation.instrumentation_tools import extend_otel_exception_recording

extend_otel_exception_recording()


class Configuration:

    def __init__(self):
        self.environment = os.environ.get('ENVIRONMENT', 'DEV')
        self.commit_id = os.environ.get('GIT_COMMIT_ID', '')
        self.this_package_root = None
        self.other_package_roots = []

    def set_environment(self, value: str) -> 'Configuration':
        self.environment = value
        return self

    def set_commit_id(self, value: str) -> 'Configuration':
        self.commit_id = value
        return self

    def trace_this_package(self, root='./') -> 'Configuration':
        current_frame = inspect.currentframe()
        caller_frame = inspect.getouterframes(current_frame)[1]
        package_root = os.path.realpath(os.path.join(os.path.dirname(caller_frame.filename), root))
        self.this_package_root = package_root.replace('\\', '/')
        return self

    def trace_package(self, module_name: str) -> 'Configuration':
        spec = util.find_spec(module_name)
        if not spec:
            raise ValueError(f'Module {module_name} was not found')
        for path in spec.submodule_search_locations:
            self.other_package_roots.append(path.replace('\\', '/'))
        return self

    @property
    def resource(self):
        return Resource(attributes={
            DEPLOYMENT_ENVIRONMENT: self.environment,
            'commit_id': self.commit_id,
            'paths.this_package_root': self.this_package_root,
            'paths.other_package_roots': self.other_package_roots,
            'paths.venv_root': os.getenv('VIRTUAL_ENV'),
            'paths.working_directory': os.getcwd().replace('\\', '/'),
            'a': BoundedAttributes(attributes={
                'b': 1
            })
        })

    @property
    def span_processor(self):
        otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:5050", insecure=True)
        span_processor = BatchSpanProcessor(otlp_exporter)
        return span_processor
