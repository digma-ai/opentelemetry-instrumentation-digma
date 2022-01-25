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

    _attributes = {
        'exception.locals': _get_locals_statistics(ex)
    }
    if attributes:
        _attributes.update(attributes)
    return default_record_exception(self, exception, _attributes, timestamp, escaped)


def _get_frame_id(frame,line_number):
    return f"{frame.f_code.co_filename}/{frame.f_code.co_name}:{line_number}"


def _extract_local_info(local_name, local_obj) -> dict:
    local_stats = {"length": 0,
                   "is_none": (local_obj == 'None'),
                   "type": str(type(local_obj)),
                   "value": ""}

    if isinstance(local_obj, list) or isinstance(local_obj, str):
        local_stats["length"] = str(len(local_obj))

    elif isinstance(local_obj, Enum) or isinstance(local_obj, float)\
            or isinstance(local_obj, int) or isinstance(local_obj, bool):
        local_stats["value"] = str(local_obj)

    return local_stats


def _extract_class_info(local_name, local_obj):
    match = re.match('<(.*) object at .*>', local_obj)
    if match:
        return match.group(1)
    return ""


def _extract_frames_info(ex: Exception):
    if ex.__cause__ is not None:
        yield from _extract_frames_info(ex.__cause__)
    elif ex.__context__ is not None and not ex.__suppress_context__:
        yield from _extract_frames_info(ex.__context__)

    for frame, line in traceback.walk_tb(ex.__traceback__):
        locals_stats = {}
        frame_class = ""
        if frame.f_locals:
            for local in frame.f_locals:
                localobj = frame.f_locals[local]
                if local == 'self':
                    frame_class = type(localobj).__name__
                else:
                    locals_stats[local] = _extract_local_info(local, localobj)

            yield _get_frame_id(frame, line), {"class": frame_class, "locals": locals_stats}


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


def _get_locals_statistics(tbe: traceback):
    # locals = list(_recursively_extract_locals(tbe))
    frame_extra_info = dict(_extract_frames_info(tbe))
    return json.dumps(frame_extra_info)

def extend_otel_exception_recording():
    Span.record_exception = record_exception
