# opentelemetry-instrumenation-digma
[![Tests](https://github.com/digma-ai/opentelemetry-instrumentation-digma/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/digma-ai/opentelemetry-instrumentation-digma/actions/workflows/unit-tests.yml) [![PyPI version](https://badge.fury.io/py/opentelemetry-instrumentation-digma.svg)](https://badge.fury.io/py/opentelemetry-instrumentation-digma)

This package provides instrumentation helpers and tools to make it easy to set up Digma to work along with your OpenTelemetry instrumentation.

In order to be able to effectively glean code-object based insights for continuous feedback and map them back in the IDE, Digma inserts additional attribute into the OTEL resource attributes. 

[Installing the package](#installing) 

[Instrumenting existing projects](#instrumenting_existing) 

[The Digma instrumentation helper configuration options](#the-digma-instrumentation-helper-configuration-options)

[The Tracing decorator](#the-tracing-decorator)

<a name="installing"/>

## Installing the package
```bash
pip install opentelemetry-instrumentation-digma
```

<a name="instrumenting_existing"/>
## Instrumenting an existing project

### If you are introducing both OTEL and Digma

To make it convenient to get started quickly with some default for both OpenTelemetry and Digma, a quick bootsrap function is provided. This is not intended for usage if you already have OpenTelmetry set up in your project, nor be used as a production configuration.

```python
from opentelemetry.instrumentation.digma import digma_opentelemetry_boostrap

digma_opentelemetry_boostrap(service_name='server-name', digma_backend="http://localhost:5050",
                             configuration=DigmaConfiguration().trace_this_package())
```

### If you are already using OpenTelemtry tracing in your project

If you have an existing OpenTelemtry instrumentaiton set up, simply use the DigmaConfiguration object to create a `Resource `object and merge it with your resource to import all of the needed attributes. 

```python
resource = Resource.create(attributes={SERVICE_NAME: service_name})
resource = resource.merge(DigmaConfiguration().trace_this_package())
```
You can use a standard OTLP exporter to the Digma collector for local deployments:

```python
exporter = OTLPSpanExporter(endpoint="localhost:5050", insecure=True)
provider.add_span_processor(BatchSpanProcessor(exporter))
```

Alternative, if you're already using a collector component you can simply modify its configuration file:
```yaml
exporters:
...
otlp/digma:
    endpoint: "localhost:5050"
    tls:
      insecure: true
service:
  pipelines:
    traces:
      exporters: [otlp/digma, ...]
```

## Building the package from source

```bash
python -m build
```

<a name="the-digma-instrumentation-helper-configuration-options"/>

## The Digma instrumentation helper configuration options

| Setting          | Description           | Default  |
| ---------------- |-------------  | -----|
| `set_environment`|  Set the identifier of the deployment environment  for the current trace process. e.g. 'staging', 'ci'| Will try to read from env variable, otherwies 'UNSET' |
| `set_commit_id`      | Allows setting the commit identifier for the currently executing code.       |   Will try to read from env variable otherwise empty |
| `use_env_variable_for_commit_id` | Set a custom environment variable to read the commit identifier from in runtime.     |  'GIT_COMMIT_ID' | 
| `use_env_variable_for_deployment_environment` | Set a custom environment variable to read the deployment environment identifier from in runtime. | 'DEPLOYMENT_ENV' |
| `trace_this_package` | Specify the current package root folder. Used to aligned tracing with code | None |
| `trace_package` | Specify additional satellite or infra packages to track | None 


<a name="the-tracing-decorator"/>

## The tracing decorator

The digma package include an optional tracing decorator intended to make span declarations easier 
and less repetitive. You can use the decorator at the function or class level to specify 
a span should be automatically created.

Example usage:
```python 
@instrument
def standalone_function(self):
    # Will create a span named 'standalone_function' (default naming)
    pass
    
@instrument(attributes={"one": "two"})
class SomeClass:

    @instrument(span_name="function_decorator", attributes={"two": "three"})
    def function_one(self):
        # Will create a span named 'function_decorator' with above attributes
        pass

    def function_two(self):
        # Will create a span named 'function_two', since SomeClass has decorator
        pass
   
    def _function_three(self):
        # Will not create a span for this function as it is private
        pass

    @instrument(ignore=True)
    def do_not_instrument(self):
        # Will not create a span for this function as it is set to ignore
        pass
```

