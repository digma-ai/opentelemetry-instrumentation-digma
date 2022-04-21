from opentelemetry.trace import Span
import time
import datetime


class TestHelpers:

    @staticmethod
    def create_errors_over_timespan(error_request, message, iterations, create_time_headers):
        print(message)
        for i in range(1, iterations):
            print(f"iteration {i}", end='\r', flush=True)
            headers = create_time_headers(i)
            error_request(headers)
            time.sleep(0.2)
        print("\n")

    @staticmethod
    def get_timestamp_header(initial_time: datetime.timedelta, interval: datetime.timedelta, iteration):
        new_time = datetime.datetime.now() + initial_time + (interval * iteration)
        if new_time > datetime.datetime.now():
            new_time = datetime.datetime.now()
        timestamp = str(int(datetime.datetime.timestamp(new_time) * 1000000000))
        return {'x-simulated-time': timestamp}


class OpenTelemetryTimeOverride:

    @staticmethod
    def test_overrides(spans):
        simulated_spans = [span for span in spans if (span.attributes and 'x-simulated-time' in span.attributes)]
        if not simulated_spans:
            return
        root_span=simulated_spans[0]
        if root_span:
            new_time = int(root_span.attributes['x-simulated-time'])

            for span in spans:
                delta = span.start_time-root_span.start_time
                duration = span.end_time-span.start_time

                for event in span.events:
                    delta = event.timestamp - span.start_time
                    event._timestamp=new_time+delta

                span._start_time = new_time + delta
                span._end_time = span.start_time + duration


class FastApiTestInstrumentation:

    @staticmethod
    def client_request_hook(span: Span, scope: dict):
        if span and span.is_recording():
            span.set_attribute("custom_user_attribute_from_client_request_hook", "some-value")

    @staticmethod
    def client_response_hook(span: Span, message: dict):
        if span and span.is_recording():
            span.set_attribute("custom_user_attribute_from_response_hook", "some-value")

    @staticmethod
    def server_request_hook(span: Span, scope: dict):
        if span and span.is_recording():
            for header, value in scope['headers']:
                if header == b'x-simulated-time':
                    span.set_attribute('x-simulated-time', value)