from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue
from opentelemetry.proto.trace.v1.trace_pb2 import Span as ProtoSpan, Status as ProtoStatus
from opentelemetry.sdk.trace import Event, Span
from opentelemetry.trace import SpanKind, Link, Status
from opentelemetry.trace import StatusCode


def _create_proto_event(event: Event) -> ProtoSpan.Event:
    attributes = []
    for attribute in event.attributes:
        attributes.append(KeyValue(key=attribute, value=AnyValue(string_value=str(event.attributes[attribute]))))
    return ProtoSpan.Event(time_unix_nano=event.timestamp,
                           name=event.name,
                           attributes=attributes)


def _convert_span_kind(span_kind: SpanKind):
    if span_kind == SpanKind.CLIENT:
        return ProtoSpan.SPAN_KIND_CLIENT
    if span_kind == SpanKind.CONSUMER:
        return ProtoSpan.SPAN_KIND_CONSUMER
    if span_kind == SpanKind.INTERNAL:
        return ProtoSpan.SPAN_KIND_INTERNAL
    if span_kind == SpanKind.PRODUCER:
        return ProtoSpan.SPAN_KIND_PRODUCER
    if span_kind == SpanKind.SERVER:
        return ProtoSpan.SPAN_KIND_SERVER
    else:
        return ProtoSpan.SPAN_KIND_UNSPECIFIED


def _create_proto_link(link: Link):
    attributes = []
    for attribute in link.attributes:
        attributes.append(KeyValue(key=attribute, value=AnyValue(string_value=str(link.attributes[attribute]))))

    return ProtoSpan.Link(trace_id=bytes(str(link.context.trace_id)),
                          trace_state=str(link.context.trace_state),
                          attributes=attributes)


def _convert_status_code(code: StatusCode):
    if code == StatusCode.ERROR:
        return ProtoStatus.StatusCode.STATUS_CODE_ERROR
    if code == StatusCode.OK:
        return ProtoStatus.StatusCode.STATUS_CODE_OK
    else:
        return ProtoStatus.StatusCode.STATUS_CODE_UNSET


def _create_proto_status(status: Status):
    return ProtoStatus(message=status.description,
                       code=_convert_status_code(status.status_code))


def _create_proto_span(span: Span) -> ProtoSpan:
    attributes = []
    for attribute in span.attributes:
        attributes.append(KeyValue(key=attribute, value=AnyValue(string_value=str(span.attributes[attribute]))))

    proto_events = [_create_proto_event(event) for event in span.events]
    links = [_create_proto_link(link) for link in span.links]
    return ProtoSpan(span_id=bytes(str(span.context.span_id), 'utf-8'),
                     trace_id=bytes(str(span.context.trace_id), 'utf-8'),
                     parent_span_id=bytes(str(span.parent.span_id), 'utf-8') if span.parent else None,
                     name=span.name, kind=_convert_span_kind(span.kind), start_time_unix_nano=span.start_time,
                     end_time_unix_nano=span.end_time, dropped_attributes_count=span.dropped_attributes,
                     events=proto_events, dropped_events_count=span.dropped_events,
                     links=links, status=_create_proto_status(span.status))
