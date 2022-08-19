import pytest
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor, ReadableSpan

from opentelemetry import trace
from opentelemetry.instrumentation.digma.trace_decorator import instrument, TracingDecoratorOptions
from stubs.python_module import A, C, B
from stubs.python_module import ClassWithStaticMethods


class TestSpanDecorator:

    class TestSpanProcessor(SpanProcessor):
        def __init__(self):
            self.last_span = None
            self.spans = []

        def reset(self):
            self.spans = []
            self.last_span = None

        def on_end(self, span: "ReadableSpan") -> None:
            self.last_span = span
            self.spans.append(span)

    span_processor: TestSpanProcessor = None

    @classmethod
    def setup_class(cls):
        resource = Resource.create(attributes={SERVICE_NAME: "test"})
        provider = TracerProvider(resource=resource)
        TestSpanDecorator.span_processor = TestSpanDecorator.TestSpanProcessor()
        provider.add_span_processor(TestSpanDecorator.span_processor)
        trace.set_tracer_provider(provider)

    def setup_method(self, method):
        TestSpanDecorator.span_processor.reset()
        TracingDecoratorOptions.set_default_attributes({})
        TracingDecoratorOptions.set_naming_scheme(TracingDecoratorOptions.NamingSchemes.default_scheme)

    @instrument
    def test_decorated_function_gets_instrumented_automatically_with_span(self):
        assert trace.get_current_span().is_recording() is True

    def test_none_decorated_function_does_not_instrument_automatically_with_span(self):
        assert trace.get_current_span().is_recording() is False

    @instrument(span_name="blah")
    def test_can_set_specific_name_for_span(self):
        assert trace.get_current_span().is_recording() is True
        assert trace.get_current_span().name is 'blah'

    @instrument
    def test_can_set_naming_scheme_for_spans(self, custom_naming_scheme):
        assert trace.get_current_span().name is custom_naming_scheme(self.test_can_set_naming_scheme_for_spans)

    @instrument(span_name="some_name")
    def test_explicit_span_name_overrides_policy(self, custom_naming_scheme):
        assert trace.get_current_span().name is not custom_naming_scheme(self.test_can_set_naming_scheme_for_spans)
        assert trace.get_current_span().name is 'some_name'

    @instrument(attributes={'test': 'blah'})
    def test_span_attributes_set_by_decorator(self, custom_naming_scheme):
        assert trace.get_current_span().attributes['test'] is 'blah'

    @instrument
    def test_span_attributes_set_by_default_options(self, default_attributes_option):
        for att in default_attributes_option:
            assert trace.get_current_span().attributes[att] is default_attributes_option[att]

    def test_exeception_recorded_by_span_by_default(self, custom_naming_scheme):
        try:
            self.execption_raising_span()
        except:
            span = TestSpanDecorator.span_processor.last_span
            assert span.events
            error_event = span.events[0]
            assert error_event.attributes["exception.message"] is 'blah'

    def test_exeception_not_recorded_by_span_if_requested(self, custom_naming_scheme):
        try:
            self.execption_raising_span_record_exception_false()
        except:
            span = TestSpanDecorator.span_processor.last_span
            assert not span.events

    @instrument
    def execption_raising_span(self):
        raise Exception("blah")

    @instrument(record_exception=False)
    def execption_raising_span_record_exception_false(self):
        raise Exception("blah")

    def test_instrument_class_instruments_class_functions_without_decorator(self):
        a = A()
        a.function_one()
        assert TestSpanDecorator.span_processor.last_span.name == 'A.function_one'

    def test_if_both_class_and_function_are_decorated_only_function_decorator_is_called(self):
        c = C()
        c.function_one()
        assert len(TestSpanDecorator.span_processor.spans) == 1
        last_span = TestSpanDecorator.span_processor.last_span
        assert last_span.attributes.get('one') is None
        assert last_span.attributes.get('two') == 'three'
        assert last_span.name == 'function_decorator'

    def test_instrument_class_can_auto_set_attributes(self):
        c = C()
        c.function_two()
        last_span = TestSpanDecorator.span_processor.last_span
        assert last_span.attributes.get('one') == 'two'

    def test_existing_decorators_dont_affect_tracing_decorator(selfs):
        b = B()
        b.function_two()
        last_span = TestSpanDecorator.span_processor.last_span
        assert last_span.attributes.get('two') == 'three'

    def test_ignored_functions_not_instrumented_by_class_decorator(selfs):
        c = C()
        c.do_not_instrument()
        last_span = TestSpanDecorator.span_processor.last_span
        assert len(TestSpanDecorator.span_processor.spans) == 0

    def test_can_decorate_class_with_static_function(self):
        ClassWithStaticMethods.function_one()
        assert len(TestSpanDecorator.span_processor.spans) == 1
        last_span = TestSpanDecorator.span_processor.last_span
        assert last_span.attributes.get('one') == 'two'
        assert last_span.name == 'ClassWithStaticMethods.function_one'

    def test_can_decorate_class_with_static_function_calling_method_on_instance(self):
        c = ClassWithStaticMethods()
        c.function_one()
        assert len(TestSpanDecorator.span_processor.spans) == 1
        last_span = TestSpanDecorator.span_processor.last_span
        assert last_span.attributes.get('one') == 'two'
        assert last_span.name == 'ClassWithStaticMethods.function_one'

@pytest.fixture
def custom_naming_scheme():
    def naming_callback(func):
        return 'blah'

    TracingDecoratorOptions.set_naming_scheme(naming_callback)
    return naming_callback


@pytest.fixture
def default_attributes_option():
    attributes = {'default': 'blah'}
    TracingDecoratorOptions.set_default_attributes(attributes)
    return attributes
