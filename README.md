# opentelemetry-instrumenation-digma
[![Tests](https://github.com/digma-ai/opentelemetry-instrumentation-digma/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/digma-ai/opentelemetry-instrumentation-digma/actions/workflows/unit-tests.yml) [![PyPI version](https://badge.fury.io/py/opentelemetry-instrumentation-digma.svg)](https://badge.fury.io/py/opentelemetry-instrumentation-digma)

This package provides instrumentation helpers and tools to make it easy to set up Digma to work along with your OpenTelemetry instrumentation.

In order to be able to effectively glean code-object based insights for continuous feedback and map them back in the IDE, Digma inserts additional attribute into the OTEL resource attributes. 

To make it easy to use Digma, we've created this helper package.

### Installing the package
```bash
pip install opentelemetry-instrumentation-digma
```

### Building the package from source

```bash
python -m build
```

### Instrumenting an existing project

#### If you are introducing both OTEL and Digma

To make it convenient to get started quickly with some default for both OpenTelemetry and Digma, a quick bootsrap function is provided. This is not intended for usage if you already have OpenTelmetry set up in your project, nor be used as a production configuration.

```python
from opentelemetry.instrumentation.digma import digma_opentelemetry_boostrap

digma_opentelemetry_boostrap(service_name='server-name', digma_backend="http://localhost:5050",
                             configuration=DigmaConfiguration().trace_this_package())
```

#### If you are already using OpenTelemtry tracing in your project

If you have an existing OpenTelemtry instrumentaiton set up, simply use the DigmaConfiguration object to create a `Resource `object and merge it with your resource to import all of the needed attributes. 

```python
resource = Resource.create(attributes={SERVICE_NAME: service_name})
resource = resource.merge(DigmaConfiguration().trace_this_package())
```
#### The Digma configuration options

| Setting          | Description           | Default  |
| ---------------- |-------------  | -----|
| `set_environment`|  Set the identifier of the deployment environment  for the current trace process. e.g. 'staging', 'ci'| Will try to read from env variable, otherwies 'UNSET' |
| `set_commit_id`      | Allows setting the commit identifier for the currently executing code.       |   Will try to read from env variable otherwise empty |
| `use_env_variable_for_commit_id` | Set a custom environment variable to read the commit identifier from in runtime.     |  'GIT_COMMIT_ID' | 
| `use_env_variable_for_deployment_environment` | Set a custom environment variable to read the deployment environment identifier from in runtime. | 'DEPLOYMENT_ENV' |
| `trace_this_package` | Specify the current package root folder. Used to aligned tracing with code | None |
| `trace_package` | Specify additional satellite or infra packages to track | None 
