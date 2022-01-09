import sys
import traceback
from enum import Enum
from typing import Optional
import json
from opentelemetry.sdk.trace import Span
from opentelemetry.util import types
import re

default_record_exception = Span.record_exception


def record_exception(
        self,
        exception: Exception,
        attributes: types.Attributes = None,
        timestamp: Optional[int] = None,
        escaped: bool = False,
) -> None:
    ex = sys.exc_info()[1]
    if not ex:
        return None

    tbe = traceback.TracebackException.from_exception(
        ex, limit=None, capture_locals=True)

    _attributes = {
        'exception.stacktrace.full': _get_traceback_with_locals(tbe),
        'exception.locals': _get_locals_statistics(tbe)
    }
    if attributes:
        _attributes.update(attributes)
    return default_record_exception(self, exception, _attributes, timestamp, escaped)


def _get_frame_id(frame: traceback.FrameSummary):
    return f"{frame.filename}/{frame.name}:{frame.lineno}"


def _extract_local_info(local_name, local_obj) -> dict:
    local_stats = {"length": "",
                   "is_none": (local_obj == 'None'),
                   "type": str(type(local_obj)),
                   "enum_value": ""}

    if isinstance(local_obj, list) or isinstance(local_obj, str):
        local_stats["length"] = str(len(local_obj))

    if isinstance(local_obj, Enum):
        local_stats["enum_value"] = local_obj

    return local_stats


def _extract_class_info(local_name, local_obj):
    match = re.match('<(.*) object at .*>', local_obj)
    if match:
        return match.group(1)
    return ""


def _extra_frame_info(tbe: traceback.TracebackException):
    if tbe.__cause__ is not None:
        yield from _extra_frame_info(tbe.__cause__)
    elif tbe.__context__ is not None and not tbe.__suppress_context__:
        yield from _extra_frame_info(tbe.__context__)

    for frame in tbe.stack:
        locals_stats = {}
        frame_class = ""
        if frame.locals:

            for local in frame.locals:
                localobj = frame.locals[local]
                if local == 'self':
                    frame_class = _extract_class_info(local, localobj)
                else:
                    locals_stats[local] = _extract_local_info(local, localobj)


            yield _get_frame_id(frame), {"class": frame_class, "locals": locals_stats}


#
# def _recursively_extract_locals(tbe: traceback.TracebackException):
#     if tbe.__cause__ is not None:
#         yield from _recursively_extract_locals(tbe.__cause__)
#     elif tbe.__context__ is not None and not tbe.__suppress_context__:
#         yield from _recursively_extract_locals(tbe.__context__)
#
#     for frame in tbe.stack:
#         locals_stats = {}
#         frame_class = ""
#         if frame.locals:
#
#             for local in frame.locals:
#                 localobj = frame.locals[local]
#                 locals_stats[local] = {}
#                 if isinstance(localobj, list) or isinstance(localobj, str):
#                     locals_stats[local]["is_none"] = (localobj == 'None')
#                     locals_stats[local]['type'] = str(type(localobj))
#                     if local == 'self':
#                         frame_class = re.match('<(.*) object at .*>', localobj).group(1)
#                     elif localobj is list and len(localobj) > 10:
#                         locals_stats[local]["length"] = str(len(localobj))
#                     elif localobj is str and len(localobj) > 64:
#                         locals_stats[local]["length"] = str(len(localobj))
#
#         local_info = {
#             "module_path": frame.filename,
#             "module_name": frame.name,
#             "executed_code": frame.line,
#             "line_number": frame.lineno,
#             "locals": locals_stats,
#             "class": frame_class,
#             "name": frame.name,
#             "line": frame.line,
#             "line_number": frame.lineno
#         }
#
#         yield json.dumps(local_info)
#

def _get_locals_statistics(tbe: traceback.TracebackException):
    # locals = list(_recursively_extract_locals(tbe))
    frame_extra_info = dict(_extra_frame_info(tbe))
    return json.dumps(frame_extra_info)


def _get_traceback_with_locals(tbe: traceback.TracebackException):
    st = list(iter(tbe.format()))

    full_trace = str.join('\n', st)

    return full_trace


def extend_otel_exception_recording():
    Span.record_exception = record_exception