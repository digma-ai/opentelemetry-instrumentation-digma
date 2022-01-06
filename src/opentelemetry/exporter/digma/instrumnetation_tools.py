import traceback

from opentelemetry.sdk.trace import Span
from typing import Optional
from opentelemetry.util import types
import opentelemetry.exporter.digma.common as common
import sys

default_record_exception = Span.record_exception


def record_exception(
        self,
        exception: Exception,
        attributes: types.Attributes = None,
        timestamp: Optional[int] = None,
        escaped: bool = False,
) -> None:
    _attributes = {'exception.stacktrace.full': _get_traceback_with_locals(sys.exc_info()[1])}
    if attributes:
        _attributes.update(attributes)
    return default_record_exception(self, exception, _attributes, timestamp, escaped)


def _get_traceback_with_locals(ex: Exception):
    if not ex:
        return None

    st = list(iter(traceback.TracebackException.from_exception(
        ex, limit=None, capture_locals=True).format()))

    full_trace = str.join('\n', st)

    return full_trace


def extend_otel_expansion_recording():
    Span.record_exception = record_exception
