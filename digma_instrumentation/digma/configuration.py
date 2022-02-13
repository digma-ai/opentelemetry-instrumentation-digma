import inspect
import os
from importlib import util
from opentelemetry.sdk.resources import Resource, DEPLOYMENT_ENVIRONMENT

from digma.instrumnetation_tools import extend_otel_exception_recording

extend_otel_exception_recording()


class Configuration:

    def __init__(self):
        self.environment = os.environ.get('ENVIRONMENT', 'DEV')
        self.commitId = os.environ.get('GIT_COMMIT_ID', '')
        self.traceablePaths = []

    def trace_this_package(self, root='./'):
        current_frame = inspect.currentframe()
        caller_frame = inspect.getouterframes(current_frame)[1]
        package_root = os.path.realpath(os.path.join(os.path.dirname(caller_frame.filename), root))
        self.traceablePaths.append(package_root.replace('\\', '/'))
        return self

    def trace_package(self, module_name: str) -> 'Configuration':
        spec = util.find_spec(module_name)
        if not spec:
            raise ValueError(f'Module {module_name} was not found')
        for path in spec.submodule_search_locations:
            self.traceablePaths.append(path.replace('\\', '/'))
        return self

    @property
    def resource(self):
        return Resource(attributes={
            DEPLOYMENT_ENVIRONMENT: self.environment,
            'commitId': self.commitId,
            'traceableFilePaths': self.traceablePaths
        })
