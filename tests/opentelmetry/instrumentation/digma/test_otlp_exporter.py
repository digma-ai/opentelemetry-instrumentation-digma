from typing import Sequence, Dict, List

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult


class OTLPSpanExporterForTests(OTLPSpanExporter):
    def __init__(self, endpoint: str, insecure: bool):
        super().__init__(endpoint=endpoint, insecure=insecure)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self.update_timestamps(spans)
        return super().export(spans)

    @staticmethod
    def update_timestamps(spans: Sequence[ReadableSpan]):
        traces: Dict[str, List[ReadableSpan]] = {}
        for span in spans:
            trace_id = span.context.trace_id
            traces.setdefault(trace_id, []).append(span)

        for trace_id, trace_spans in traces.items():
            simulated_spans = [span for span in trace_spans if (span.attributes and 'x-simulated-time' in span.attributes)]
            if not simulated_spans:
                continue

            root = simulated_spans[0]
            new_time = int(root.attributes['x-simulated-time'])

            for span in trace_spans:
                delta = span.start_time - root.start_time
                duration = span.end_time - span.start_time

                for event in span.events:
                    delta = event.timestamp - span.start_time
                    event._timestamp = new_time + delta

                span._start_time = new_time + delta
                span._end_time = span.start_time + duration

