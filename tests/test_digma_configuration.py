import string
import random
from unittest import TestCase
import os

# test
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT
from src.opentelemetry.instrumentation.digma import DigmaConfiguration
from src.opentelemetry.instrumentation.digma.resource_attributes import *

class DigmaConfigurationTests(TestCase):

    def setUp(self):
        self.digma_configuration = DigmaConfiguration()

    @staticmethod
    def _get_random_string(characters: int):
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(characters))

    def test_if_no_explicit_commit_id_provided_defaults_to_default_env_variable(self):
        commit_id = DigmaConfigurationTests._get_random_string(10)
        os.environ[DigmaConfiguration.DEFAULT_ENV_VARIABLE_COMMIT_ID]=commit_id
        resource_commit_id = self.digma_configuration.resource.attributes[COMMIT_ID]
        self.assertEqual(resource_commit_id, commit_id)

    def test_commit_id_is_provided_env_variable_still_used(self):
        env_commit_id = DigmaConfigurationTests._get_random_string(10)
        os.environ[DigmaConfiguration.DEFAULT_ENV_VARIABLE_COMMIT_ID]=env_commit_id

        explicit_commit_id = DigmaConfigurationTests._get_random_string(10)

        self.digma_configuration.set_commit_id(explicit_commit_id)
        commit_id_actual = self.digma_configuration.resource.attributes[COMMIT_ID]
        self.assertEqual(commit_id_actual, env_commit_id)
        self.assertNotEqual(commit_id_actual, explicit_commit_id)

    def test_uses_explicitly_provided_environment_variable_for_commit_id(self):
        env_commit_id = DigmaConfigurationTests._get_random_string(10)
        custom_env_variable = 'CUSTOM_ENV_COMMIT_ID'
        os.environ[custom_env_variable] = env_commit_id

        self.digma_configuration.use_env_variable_for_commit_id(custom_env_variable);
        
        resource_commit_id = self.digma_configuration.resource.attributes[COMMIT_ID]
        self.assertEqual(resource_commit_id, env_commit_id)

    def test_if_no_explicit_deploymet_env_provided_defaults_to_default_env_variable(self):
        environment_id = DigmaConfigurationTests._get_random_string(10)
        os.environ[DigmaConfiguration.DEFAULT_ENV_VARIABLE_DEPLOYMENT_ENV]=environment_id
        resource_commit_id = self.digma_configuration.resource.attributes[DEPLOYMENT_ENVIRONMENT]
        self.assertEqual(resource_commit_id, environment_id)

    def test_explicit_deploymet_env_provided_env_variable_still_used(self):
        env_deployment_env= DigmaConfigurationTests._get_random_string(10)
        os.environ[DigmaConfiguration.DEFAULT_ENV_VARIABLE_DEPLOYMENT_ENV]=env_deployment_env

        explicit_deployment_env = DigmaConfigurationTests._get_random_string(10)

        resource_deployment_env = self.digma_configuration.set_environment(explicit_deployment_env).resource.attributes[DEPLOYMENT_ENVIRONMENT]
        self.assertEqual(resource_deployment_env, env_deployment_env)
        self.assertNotEqual(resource_deployment_env, explicit_deployment_env)

    def test_will_use_alternative_commmit_env_variable(self):
        environment_id = DigmaConfigurationTests._get_random_string(10)
        environment_key = DigmaConfigurationTests._get_random_string(5)

        os.environ[environment_key]=environment_id
        self.digma_configuration.use_env_variable_for_commit_id(environment_key)
        resource_commit_id =self.digma_configuration.resource.attributes[COMMIT_ID]
        self.assertEqual(resource_commit_id, environment_id)

    def test_will_use_alternative_deploymentenv_env_variable(self):
        environment_id = DigmaConfigurationTests._get_random_string(10)
        environment_key = DigmaConfigurationTests._get_random_string(5)

        os.environ[environment_key]=environment_id
        self.digma_configuration.use_env_variable_for_deployment_environment(environment_key)
        deployment_env = self.digma_configuration.resource.attributes[DEPLOYMENT_ENVIRONMENT]
        self.assertEqual(deployment_env, environment_id)