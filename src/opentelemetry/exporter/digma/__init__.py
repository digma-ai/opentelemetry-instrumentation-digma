import json
import logging
import os
from typing import Sequence, List

import grpc
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

import opentelemetry.exporter.digma.common as common
from conf import LazyConfig
from opentelemetry.exporter.digma.instrumnetation_tools import extend_otel_exception_recording
from opentelemetry.exporter.digma.proto_conversions import _create_proto_event
from opentelemetry.exporter.digma.traceback_parser import TracebackParser
from .proto_conversions import _convert_span_kind, _create_proto_link, _convert_status_code, _create_proto_status, \
    _create_proto_span
from .v1.digma_pb2 import ExportRequest, ExtendedSpan, ErrorFrame, ErrorEvent, ErrorFrameStack
from .v1.digma_pb2_grpc import DigmaCollectorStub
from conf import config

logger = logging.getLogger(__name__)

extend_otel_exception_recording()


class LocalsStat(object):


    def __init__(self, name, is_none, length,type, value):
        self.name=name
        self.is_none = is_none
        self.length = length
        self.type =type
        self.value=value
        super().__init__()

# Span.add_event = add_event
class LocalsFrame(object):
    def __init__(self, module_path :str, module_name:str, executed_code :str,
                 line_number: str, module_class :str, local_stats: List[LocalsStat]) -> None:
        super().__init__()
        self.module_class = module_class
        self.line_number = line_number
        self.executed_code = executed_code
        self.module_path = module_path
        self.local_stats=local_stats
        self.module_name=module_name


class DigmaExporter(SpanExporter):

    SERVICE_PORT_VAR = "DIGMA_PORT"
    SERVICE_ADDRESS_VAR = "DIGMA_SERVER"

    def __init__(self) -> None:
        self._closed = False
        super().__init__()

    def export(self, spans: Sequence[Span]) -> SpanExportResult:

        if not self._spans_contain_exception_event(spans):
            return SpanExportResult.SUCCESS

        extended_spans = self._build_extended_spans(spans)

        export_request = ExportRequest(
            environment=os.environ.get('ENVIRONMENT', ''),
            commit_id=os.environ.get('GIT_COMMIT_ID', ''),
            programming_language='python',
            spans=extended_spans
        )
        if self._closed:
            logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE

        address, port = self._get_service_server_and_port()
        channel = grpc.insecure_channel(f'{address}:{port}')

        def process_response(call):
            print("Greeter client received: " + call.result().message)
            channel.close()

        stub = DigmaCollectorStub(channel)
        call_future = stub.Export.future(export_request)
        call_future.add_done_callback(process_response)

    def _get_service_server_and_port(self):
        backend_port = 5050

        if self.SERVICE_PORT_VAR in os.environ:
            backend_port = os.environ.get(self.SERVICE_PORT_VAR)
        elif hasattr(config, "DIGMA_PORT"):
            backend_port = config.DIGMA_PORT
        else:
            backend_port = '5050'

        if self.SERVICE_PORT_VAR in os.environ:
            backend_address = os.environ.get(self.SERVICE_ADDRESS_VAR)
        elif hasattr(config, "DIGMA_SERVER"):
            backend_address = config.DIGMA_SERVER
        else:
            backend_address = 'localhost'

        return backend_address, backend_port



    @staticmethod
    def _generate_error_flow_name(exception_type: str, error_frame_stack: ErrorFrameStack):
        return f"{exception_type} from {error_frame_stack.frames[-1].module_name}"


    @staticmethod
    def _spans_contain_exception_event(spans: Sequence[Span]) -> bool:
        for span in spans:
            for event in span.events:
                if event.name == 'exception':
                    return True
        return False

    @staticmethod
    def _parse_locals(locals_string: str) -> List[LocalsFrame]:
        result = []
        frames = locals_string.split('\n')
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

            path = TracebackParser._file_path_normalizer(dictionary['module_path'])
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
            print(span.context.trace_id)
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

    def shutdown(self) -> None:
        self._closed = True
