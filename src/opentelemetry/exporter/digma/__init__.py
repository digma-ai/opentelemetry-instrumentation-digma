import importlib
import json
import logging
import os
from typing import Sequence, List, Optional, Callable
from urllib.parse import urlparse
from grpc import insecure_channel
from grpc import StatusCode
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult, BatchSpanProcessor

import conf
import opentelemetry.exporter.digma.common as common
from conf.environment_variables import DIGMA_EXPORTER_ENDPOINT, ENVIRONMENT, GIT_COMMIT_ID
from opentelemetry import trace
from opentelemetry.exporter.digma.instrumnetation_tools import extend_otel_exception_recording
from opentelemetry.exporter.digma.proto_conversions import _create_proto_event
from opentelemetry.exporter.digma.traceback_parser import TracebackParser
from opentelemetry.exporter.digma.v1 import digma_pb2 as opentelemetry_dot_exporter_dot_digma_dot_v1_dot_digma__pb2
from .proto_conversions import _convert_span_kind, _create_proto_link, _convert_status_code, _create_proto_status, \
    _create_proto_span
from .v1.digma_pb2 import ExportRequest, ExtendedSpan, ErrorFrame, ErrorEvent, ErrorFrameStack
from .v1.digma_pb2_grpc import DigmaCollectorStub

logger = logging.getLogger(__name__)

extend_otel_exception_recording()


def register_batch_digma_exporter(endpoint: Optional[str] = None,
                                  max_queue_size: int = None,
                                  schedule_delay_millis: float = None,
                                  max_export_batch_size: int = None,
                                  export_timeout_millis: float = None,
                                  pre_processors: List[Callable[[Sequence[Span]], None]] = None):
    max_export_batch_size = max_export_batch_size if max_export_batch_size else 10
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(DigmaExporter(endpoint=endpoint, pre_processors=pre_processors), max_queue_size,
                           schedule_delay_millis,
                           max_export_batch_size, export_timeout_millis))


def ensure_digma_module_exists_in_python_path(digma_config_module: str):
    importlib.import_module(digma_config_module)


def get_digma_opentelemetry_exporter(endpoint: Optional[str] = None) -> 'DigmaExporter':
    return DigmaExporter(endpoint)


class LocalsStat(object):

    def __init__(self, name, is_none, length, type, value):
        self.name = name
        self.is_none = is_none
        self.length = length
        self.type = type
        self.value = value
        super().__init__()


# Span.add_event = add_event
class LocalsFrame(object):
    def __init__(self, module_path: str, module_name: str, executed_code: str,
                 line_number: str, module_class: str, local_stats: List[LocalsStat]) -> None:
        super().__init__()
        self.module_class = module_class
        self.line_number = line_number
        self.executed_code = executed_code
        self.module_path = module_path
        self.local_stats = local_stats
        self.module_name = module_name


class DigmaExporter(SpanExporter):

    def __init__(self, endpoint: Optional[str] = None,
                 insecure: Optional[bool] = None,
                 pre_processors: List[Callable[[Sequence[Span]], None]] = None) -> None:
        self._pre_processors = pre_processors
        endpoint = endpoint or os.environ.get(DIGMA_EXPORTER_ENDPOINT, "http://localhost:5050")
        parsed_url = urlparse(endpoint)

        if insecure is None:
            if parsed_url.scheme == "https":
                insecure = False
            else:
                insecure = True

        # take only the domain itself,.e.g. localhost:5050
        if parsed_url.netloc:
            endpoint = parsed_url.netloc

        if insecure:
            # should add compression support
            channel = insecure_channel(endpoint)
        else:
            raise NotImplementedError()

        self._export = channel.unary_unary(
            '/opentelemetry.proto.digma.v1.DigmaCollector/Export',
            request_serializer=opentelemetry_dot_exporter_dot_digma_dot_v1_dot_digma__pb2.ExportRequest.SerializeToString,
            response_deserializer=opentelemetry_dot_exporter_dot_digma_dot_v1_dot_digma__pb2.ExportResponse.FromString)

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        if self._pre_processors:
            for processor in self._pre_processors:
                processor(spans)

        extended_spans = self._build_extended_spans(spans)

        export_request = ExportRequest(
            environment=os.environ.get(ENVIRONMENT, ''),
            commit_id=os.environ.get(GIT_COMMIT_ID, ''),
            programming_language='python',
            spans=extended_spans
        )

        # todo shay not sure we should handle this case @roni?
        # if self._closed:
        #     logger.warning("Exporter already shutdown, ignoring batch")
        #     return SpanExportResult.FAILURE

        def process_response(call):
            code: StatusCode = call.code()
            if code != StatusCode.OK:
                logger.error(
                    f"Digma exporter: Failed to export span batch, error code: {code} details: {call.details()}"
                )

        fut = self._export.future(export_request)
        fut.add_done_callback(process_response)
        return SpanExportResult.SUCCESS

    @staticmethod
    def _generate_error_flow_name(exception_type: str, error_frame_stack: ErrorFrameStack):
        return f"{exception_type} from {error_frame_stack.frames[-1].module_name}"

    @staticmethod
    def _parse_locals(locals_string: str) -> List[LocalsFrame]:
        result = []
        frames = locals_string.split('\n')
        project_root = conf.try_get_project_root()

        for frame in frames:
            dictionary = json.loads(frame)
            locals_stats_dictionary = dictionary["locals"]
            local_stats = []
            for local_stat in locals_stats_dictionary:
                stat = LocalsStat(name=local_stat,
                                  is_none=locals_stats_dictionary[local_stat]["is_none"],
                                  length=locals_stats_dictionary[local_stat]["length"],
                                  value=locals_stats_dictionary[local_stat]["value"],
                                  type=locals_stats_dictionary[local_stat]["type"])
                local_stats.append(stat)

            path = TracebackParser._file_path_normalizer(dictionary['module_path'], project_root)
            result.append(LocalsFrame(module_path=path,
                                      module_name=dictionary['module_name'],
                                      executed_code=dictionary['executed_code'],
                                      line_number=dictionary['line_number'],
                                      module_class=dictionary['class'],
                                      local_stats=local_stats))
        return result

    @staticmethod
    def _build_extended_spans(spans: Sequence[Span]) -> List[ExtendedSpan]:
        expanded_spans: List[ExtendedSpan] = []
        for span in spans:
            expanded_spans.append(ExtendedSpan(base=_create_proto_span(span),
                                               service_name=span.resource.attributes['service.name'],
                                               error_events=list(DigmaExporter._extract_error_events(span))))
        return expanded_spans

    @staticmethod
    def _extract_error_events(span: Span) -> List[ErrorEvent]:
        for span_event in span.events:
            if span_event.name != 'exception':
                continue

            stack_trace = span_event.attributes['exception.stacktrace']
            locals_stats = span_event.attributes['exception.locals']
            extra_frame_info = json.loads(locals_stats)

            # We omit the otel stack from recording the exception because they are an artifact
            stacks = TracebackParser \
                .parse_error_flow_stacks(stack_trace, str(span.context.span_id),
                                         extra_frame_info=extra_frame_info,
                                         ignore_list=common.IGNORE_LIST)

            exception_type = span_event.attributes['exception.type']

            error_event = ErrorEvent(exception_message=span_event.attributes['exception.message'],
                                     exception_type=span_event.attributes['exception.type'],
                                     exception_stack=stack_trace,
                                     name=DigmaExporter._generate_error_flow_name(exception_type,
                                                                                  stacks[0]),
                                     timestamp=str(span_event.timestamp),
                                     stacks=stacks)

            yield error_event

    # todo shay not sure we should handle this case @roni?
    # def shutdown(self) -> None:
    #     self._closed = True
