import logging
import os
import traceback
from google import protobuf
import grpc
from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue
from opentelemetry.exporter.digma.v1.digma_pb2 import ErrorFrameStack, ErrorFrame
from opentelemetry.proto.trace.v1.trace_pb2 import Span as proto_span, Status as proto_status
from opentelemetry.sdk.trace import Event, Span
from opentelemetry.sdk.trace.export import SpanExporter
import sys
import traceback
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.util import types
from typing import Optional
import opentelemetry.exporter.digma.common as common
from traceback import TracebackException
from anytree import Node, RenderTree,PreOrderIter
from opentelemetry.trace import SpanKind, Link, Status
logger = logging.getLogger(__name__)
from typing import Sequence, List, Iterator
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.exporter.digma.traceback_parser import TracebackParser, TracebackFrameStack
from .v1.digma_pb2 import ExportRequest, ErrorFrame, ErrorEvent, ErrorFrameStack
from .v1.digma_pb2_grpc import DigmaCollectorStub
import sys
default_add_event = Span.add_event
default_record_exception = Span.record_exception

def record_exception(
        self,
        exception: Exception,
        attributes: types.Attributes = None,
        timestamp: Optional[int] = None,
        escaped: bool = False,
    ) -> None:
     
    _attributes = {'exception.stacktrace.full': common.get_traceback_with_locals(sys.exc_info()[1])}
    if attributes:
        _attributes.update(attributes)
    return default_record_exception(self,exception, _attributes,timestamp, escaped)
    
Span.record_exception = record_exception
#Span.add_event = add_event

class DigmaExporter(SpanExporter):

    def __init__(self) -> None:
        self._closed = False
        super().__init__()

    def _create_proto_event(self, event: Event) -> proto_span.Event:
        attributes = []
        for attribute in event.attributes:
            attributes.append(KeyValue(key=attribute, value=AnyValue(string_value=str(event.attributes[attribute]))))
        return proto_span.Event(time_unix_nano=event.timestamp,
                                name=event.name,
                                attributes=attributes)
    
    def _convert_span_kind(self, span_kind: SpanKind):

        if span_kind==SpanKind.CLIENT:
            return proto_span.SPAN_KIND_CLIENT
        if span_kind==SpanKind.CONSUMER:
            return proto_span.SPAN_KIND_CONSUMER
        if span_kind==SpanKind.INTERNAL:
            return proto_span.SPAN_KIND_INTERNAL
        if span_kind==SpanKind.PRODUCER:
            return proto_span.SPAN_KIND_PRODUCER    
        if span_kind==SpanKind.SERVER:
            return proto_span.SPAN_KIND_SERVER
        else:
            return proto_span.SPAN_KIND_UNSPECIFIED          

    def _create_proto_link(self, link:Link):
        
        attributes = []
        for attribute in link.attributes:
            attributes.append(KeyValue(key=attribute, value=AnyValue(string_value=str(span.attributes[attribute]))))

        return proto_span.Link(trace_id=link.context.trace_id,
                               trace_state=link.context.trace_state,
                               attributes=attributes)
    
    def _convert_status_code(self, code: StatusCode):
        if code == StatusCode.ERROR:
            return proto_status.StatusCode.STATUS_CODE_ERROR
        if code == StatusCode.OK:
            return proto_status.StatusCode.STATUS_CODE_OK
        else:
            return proto_status.StatusCode.STATUS_CODE_UNSET            

    def _create_proto_status(self, status:Status):
        return proto_status(message=status.description,
                            code=self._convert_status_code(status.status_code) )


    def _create_proto_span(self, span: Span) -> proto_span:
        attributes = []
        for attribute in span.attributes:
            attributes.append(KeyValue(key=attribute, value=AnyValue(string_value=str(span.attributes[attribute]))))

        proto_events = [ self._create_proto_event(event) for event in span.events]
        links = [self._create_proto_link(link) for link in span.links ]
        return proto_span( span_id=bytes(str(span.context.span_id),'utf-8'),
                          parent_span_id=bytes(str(span.parent.span_id),'utf-8') if span.parent else None,
                          name=span.name, kind=self._convert_span_kind(span.kind), start_time_unix_nano=span.start_time,
                          end_time_unix_nano=span.end_time,dropped_attributes_count=span.dropped_attributes,
                          events=proto_events,dropped_events_count=span.dropped_events, 
                          links=links, status=self._create_proto_status(span.status) )
                    

    @staticmethod
    def _generate_error_flow_name(exception_type: str, error_frame_stack: ErrorFrameStack):
        return f"{exception_type} from {error_frame_stack.frames[-1].module_name}"

    @staticmethod
    def _forward_slash_for_paths(file_path: str) -> str:
        return file_path.replace('\\', '/')

             
    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        
        spans_by_id = { span.context.span_id : span for span in spans}
        roots = common.create_span_hierarchy(spans)
        spans_infos = []
        error_events = []

        for root in roots:
            span_path_events = []
            for node in PreOrderIter(root):
                span = spans_by_id[node.name]
                events = []
                for span_event in span.events:
                    if span_event.name == 'exception':
                        stack_trace = span_event.attributes['exception.stacktrace']
                        full_stack_trace = span_event.attributes['exception.stacktrace.full']
                        stacks = TracebackParser.parse_error_flow_stacks(full_stack_trace, str(span.context.span_id),
                                                                        ['opentelemetry/trace/__init__.py',
                                                                         'opentelemetry/sdk/trace/__init__.py'])
                        exception_already_captured = False
                        for existing_event in span_path_events:
                            contained_frames = common.get_contained_frames(stacks, existing_event.stacks)
                            
                            if len(contained_frames)==common.frame_count(stacks):
                                exception_already_captured=True
                                for frame in contained_frames:
                                    frame.span_id = str(span.context.span_id)  
                        

                        if not exception_already_captured:
                            exception_type = span_event.attributes['exception.type']
                            error_event = ErrorEvent(exception_message=span_event.attributes['exception.message'],
                                                    exception_type=span_event.attributes['exception.type'],
                                                    exception_stack=stack_trace,
                                                    name=self._generate_error_flow_name(exception_type, stacks[0]),
                                                    timestamp=str(span_event.timestamp),
                                                    stacks=stacks)
                            events.append(self._create_proto_event(span_event))
                        
                            span_path_events.append(error_event)
            
            error_events += span_path_events  

        
        for event in error_events:
            print("---error---" + event.name)
            for stack in event.stacks:
                for frame in stack.frames:
                    print(f"#{frame.span_id} - {frame.module_path}/{frame.module_name}:{frame.line_number}") 
        
        errors_info = ExportRequest.ErrorsInformation(trace_id=str(span.context.trace_id),
                                                      error_events=error_events)

                
        export_request = None
        spans_infos = []
        for span in spans:
            error_events = []
            events = []
            for span_event in span.events:
                if span_event.name == 'exception':
                    full_stack_trace = span_event.attributes['exception.stacktrace.full']
                    stack_trace = span_event.attributes['exception.stacktrace']
                    stacks = TracebackParser.parse_error_flow_stacks(full_stack_trace)
                    exception_type = span_event.attributes['exception.type']
                    error_event = ErrorEvent(exception_message=span_event.attributes['exception.message'],
                                             exception_type=span_event.attributes['exception.type'],
                                             exception_stack=stack_trace,
                                             name=self._generate_error_flow_name(exception_type, stacks[0]),
                                             timestamp=str(span_event.timestamp),
                                             stacks=stacks)
                    error_events.append(error_event)
                    events.append(self._create_proto_event(span_event))
            
            if error_events:
                spans_infos.append(
                    ExportRequest.SpanInformation(span_id=str(span.context.span_id),
                                                  trace_id=str(span.context.trace_id),
                                                  error_events=error_events,
                                                  events=events))
        if not spans_infos:  # no error event, no export needed
            return SpanExportResult.SUCCESS

        proto_span_infos = [self._create_proto_span(span) for span in spans]
        export_request = ExportRequest(
            service_name=span.resource.attributes['service.name'],
            environment=os.environ.get('ENVIRONMENT', ''),
            commit_id=os.environ.get('GIT_COMMIT_ID', ''),
            programming_language='python',
            error_information=errors_info,
            spans=spans_infos,
            spans_infos=proto_span_infos
        )
        if self._closed:
            logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE

        with grpc.insecure_channel('localhost:5050') as channel:
            stub = DigmaCollectorStub(channel)
            response = stub.Export(export_request)
            print("Greeter client received: " + response.message)

    def shutdown(self) -> None:
        self._closed = True
