import inspect
import os
from importlib import util
from opentelemetry.sdk.resources import Resource, DEPLOYMENT_ENVIRONMENT

from opentelemetry.instrumentation.digma.resource_attributes import *


class DigmaConfiguration:

    DEFAULT_ENV_VARIABLE_COMMIT_ID = 'GIT_COMMIT_ID'
    DEFAULT_ENV_VARIABLE_DEPLOYMENT_ENV = 'DEPLOYMENT_ENV'

    def __init__(self):
        self._environment = ''
        self._commit_id_env_variable = DigmaConfiguration.DEFAULT_ENV_VARIABLE_COMMIT_ID
        self._deployment_environment_env_variable = DigmaConfiguration.DEFAULT_ENV_VARIABLE_DEPLOYMENT_ENV
        self._commit_id = ''
        self._this_package_root = ''
        self._other_package_roots = []

    def set_environment(self, value: str) -> 'DigmaConfiguration':
        """
        Set the identifier of the deployment environment  for this trace process. Environments can signify different
        stages of the release process such as 'staging', 'dev', 'ci' or 'production' or different deployed environments,
        such as different K8S clusters.
        :param value: the environment identifier
        :return: The configuration object
        """
        self._environment = value
        return self

    def use_env_variable_for_deployment_environment(self, variable_name: str) -> 'DigmaConfiguration':
        """
        Set the env variable used to retrieve the deployment environment. The default is 'DEPLOYMENT_ENV'.
        This value will be ignored if the deployment environment is provided explicitly via 'set_environment'
        :param variable_name: the environment variable
        :return: The configuration object
        """
        self,_deployment_environment_env_variable = variable_name
        return self

    def set_commit_id(self, value: str) -> 'DigmaConfiguration':
        """
        Set the commit identifier for this trace context. The commit identifier can be provided directly
        as a parameter. If not provided explicitly, Digma will try to look extract if from an environment variable.
        The commit identifier will be used to correlate the trace data with code changes.
        :param value: The commit identifier
        :return: The Configuration object
        """
        self._commit_id = value
        return self

    def use_env_variable_for_commit_id(self, variable_name: str) -> 'DigmaConfiguration':
        """
        Set the environment variable containing the commmit identifier for this trace context. The default value
        is 'GIT_COMMIT_ID'.
        This value will be ignored if the commit identifier is provided explicitly via 'set_commit_id'
        :param variable_name: The commit identifier environment variable
        :return: The Configuration object
        """
        self._commit_id_env_variable = variable_name
        return self

    def trace_this_package(self, root='./') -> 'DigmaConfiguration':
        """
        Use this to specify that the the current page (where this function is called from) should be traced by
        Digma. Digma uses this information to make sure to track only relevant code object and better detect endpoints
        and other code objects.
        :param root: The relative folder path to the package root (defaults to './')
        :return: The Configuration object
        """
        current_frame = inspect.currentframe()
        caller_frame = inspect.getouterframes(current_frame)[1]
        package_root = os.path.realpath(os.path.join(os.path.dirname(caller_frame.filename), root))
        self._this_package_root = package_root.replace('\\', '/')
        return self

    def trace_package(self, module_name: str) -> 'DigmaConfiguration':
        """
        Trace a additional satellitelitem packages by specifying the module name to track. Digma uses this information
        to make sure to track only relevant code object and better detect endpoints  and other code objects.
        :param module_name: The module name to trace
        :return: The Configuration object
        """
        spec = util.find_spec(module_name)
        if not spec:
            raise ValueError(f'Module {module_name} was not found')
        for path in spec.submodule_search_locations:
            self._other_package_roots.append(path.replace('\\', '/'))
        return self

    @property
    def resource(self):

        commit_id = self._commit_id
        if not commit_id:
            commit_id= os.environ.get(self._commit_id_env_variable, '')

        environment = self._environment
        if not environment:
            environment = os.environ.get(self._deployment_environment_env_variable, 'UNSET')

        return Resource(attributes={
            DEPLOYMENT_ENVIRONMENT: environment,
            COMMIT_ID: commit_id,
            THIS_PACKAGE_ROOT: self._this_package_root,
            OTHER_PACKAGE_ROOTS: self._other_package_roots,
            VENV_ROOT: os.getenv('VIRTUAL_ENV', ''),
            WORKING_DIRECTORY: os.getcwd().replace('\\', '/')
        })


