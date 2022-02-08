import json
import os
import conf
from importlib import util
from opentelemetry.sdk.resources import Resource, DEPLOYMENT_ENVIRONMENT


class DigmaConfiguration:

    def __init__(self):
        self.traceablePaths = [
            conf.try_get_project_root().replace('\\', '/')
        ]

    # def trace_this_module(self):
    #     curframe = inspect.currentframe()
    #     calframe = inspect.getouterframes(curframe, 2)
    #     print('caller name:', calframe[1][3])
    #     return self

    def trace_module(self, module_name: str) -> 'DigmaConfiguration':
        spec = util.find_spec(module_name)
        if not spec:
            raise ValueError(f'Module {module_name} was not found')
        # module_path = importlib.import_module(module_name)
        # module_path.__file__
        self.traceablePaths.append(os.path.dirname(spec.origin).replace('\\', '/'))
        return self

    @property
    def resource(self):
        return Resource(attributes={
            DEPLOYMENT_ENVIRONMENT: os.environ.get('ENVIRONMENT', ''),
            'commitId': os.environ.get('GIT_COMMIT_ID', ''),
            'traceablePaths': json.dumps(self.traceablePaths)
        })
