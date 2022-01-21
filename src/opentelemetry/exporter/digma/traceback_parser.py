import logging
import os
import re
import site
from dataclasses import dataclass
from os import path
from typing import List, Dict, Set

import math
import sys

from conf import config
from opentelemetry.exporter.digma.common import is_builtin_exception
from opentelemetry.exporter.digma.v1.digma_pb2 import ErrorFrameStack, ErrorFrame, ParameterStats

ROOT_ENV_VARIABLE = 'PROJECT_ROOT'

logger = logging.getLogger(__name__)


@dataclass
class TracebackFrame:
    fullpath: str
    line_num: int
    func_name: str
    line: str
    path: str
    parameters: str
    repeat: int = 0  # when repeat > 0, means line repeated {repeat} more times


@dataclass
class TracebackFrameStack:
    frames: List[TracebackFrame]
    exception_type: str


class TracebackParser:
    _frame_file_patten = re.compile('\s\sFile\s"(.+)",\sline ([0-9]+),\sin\s(.+)')
    _frame_code_line_pattern = re.compile('\s\s\s\s(.+)')
    _frame_locals_line_pattern = re.compile('\s\s\s\s(.+)\s=\s(.+)')
    _frame_repeat_pattern = re.compile('^\s\s\[Previous line repeated ([0-9]+) more time(s?)\]$')
    _ignore_parameters: Set[str] = {'self', '_'}

    @staticmethod
    def split(arr: List[str], size: int):
        for idx in range(math.floor(len(arr) / size)):
            yield arr[idx * size: idx * size + size]

    @staticmethod
    def parse_error_flow_stacks(stacktrace: str, span_id: str = "", extra_frame_info: dict = {}, ignore_list=[]) -> \
            List[ErrorFrameStack]:
        frames: List[ErrorFrame] = []
        stacks: List[ErrorFrameStack] = []

        lines = stacktrace.splitlines()
        line_num = 0
        skip_to_next_traceback = True
        while line_num < len(lines):
            line = lines[line_num]
            if not line.strip():  # skip on empty lines
                line_num += 1
                continue

            if skip_to_next_traceback:
                if line == 'Traceback (most recent call last):':
                    skip_to_next_traceback = False
                    frames = []
                line_num += 1
                continue
            match = TracebackParser._frame_file_patten.match(line)
            if match:
                code_line = None
                repeat = 0
                fullpath = match.group(1).strip()
                code_line_num = match.group(2).strip()
                func_name = match.group(3).strip()

                func_id = f"{fullpath}/{func_name}:{code_line_num}"
                class_name = ''
                params_statistics = []

                if func_id in extra_frame_info:
                    extra_info = extra_frame_info[func_id]
                    class_name = extra_info['class']
                    locals_stats = extra_info['locals']
                    for local in locals_stats:
                        local_stats = locals_stats[local]
                        print(f"{func_id} {local} {local_stats['type']} {str(local_stats['value'])}")
                        params_statistics.append(ParameterStats(param_name=local,
                                                                param_type=local_stats['type'],
                                                                is_none=local_stats["is_none"],
                                                                length=int(local_stats["length"]),
                                                                value=str(local_stats["value"])))

                normalize_path = TracebackParser._file_path_normalizer(fullpath)
                line_num += 1
                line = lines[line_num]
                if bool(TracebackParser._frame_code_line_pattern.match(line)):
                    code_line = line.strip()
                    line_num += 1
                    line = lines[line_num]

                parameters: Dict[str, str] = {}
                while match := TracebackParser._frame_locals_line_pattern.match(line):
                    key = match.group(1).strip()
                    if key not in TracebackParser._ignore_parameters:
                        parameters[key] = match.group(2).strip()
                    line_num += 1
                    line = lines[line_num]

                match = TracebackParser._frame_repeat_pattern.match(line)
                if match:
                    line_num += 1
                    repeat = int(match.group(1))
                if normalize_path not in ignore_list:
                    frames.append(ErrorFrame(module_name=func_name,
                                             span_id=span_id,
                                             module_path=normalize_path,
                                             executed_code=code_line,
                                             line_number=int(code_line_num),
                                             parameters=parameters,
                                             repeat=repeat,
                                             module_class=class_name,
                                             parameter_stats=params_statistics))
                continue
            if frames:
                # if frames are empty,
                # it means done processing all current traceback details
                # continue until the next traceback
                exception_info = line.split(':')
                exception_type = exception_info[0]
                exception_message = exception_info[1].strip()

                unexpected = is_builtin_exception(exception_type) \
                             and 'raise' not in lines[line_num-1]

                stacks.append(
                    ErrorFrameStack(frames=frames,
                                    exception_type=exception_type,
                                    exception_message=exception_message,
                                    unexpected=unexpected))
                skip_to_next_traceback = True
            line_num += 1
        return stacks

    @staticmethod
    def _file_path_normalizer(file_path: str) -> str:

        if not path.isabs(file_path):  # case when path start with ./
            if not file_path.startswith('./'):  # todo find better way to do it, not os specific
                return file_path
            file_path = path.relpath(file_path)
            return path.join(path.basename(os.getcwd()), file_path)
        locations = set([site.getusersitepackages()] + site.getsitepackages())
        for prefix in locations:
            if file_path.startswith(prefix):
                normalize_path = file_path[len(prefix) + 1:]
                return normalize_path

        if ROOT_ENV_VARIABLE in os.environ:
            project_root = os.environ.get(ROOT_ENV_VARIABLE)
        else:
            project_root = config.PROJECT_ROOT

        if project_root:
            prefix_parent = path.dirname(project_root)
            if TracebackParser._is_descendant_of(file_path, prefix_parent):
                normalize_path = file_path[len(prefix_parent) + 1:]
                return normalize_path
        # for k, v in sys.modules.items():
        #     print(k)
        matches = set()
        for prefix in sys.path:
            prefix_parent = path.dirname(prefix)
            if TracebackParser._is_descendant_of(file_path, prefix_parent):
                matches.add(prefix_parent)
        if len(matches) > 1:
            logger.warning(f"unable to find file '{file_path}', multiple matches found: {str.join(',', matches)}")
            return file_path
        if matches:
            match = next(iter(matches))
            return file_path[len(match) + 1:]
        return file_path

    @staticmethod
    def _is_descendant_of(file_path: str, parent_path: str) -> bool:
        return file_path.startswith(parent_path + os.sep)
