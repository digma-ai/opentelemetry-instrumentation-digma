import os
import re
import site
from dataclasses import dataclass
from typing import List, Tuple

import sys
from os import path

import math

from opentelemetry.exporter.digma.v1.digma_pb2 import ErrorFrameStack, ErrorFrame


@dataclass
class TracebackFrame:
    fullpath: str
    line_num: int
    func_name: str
    line: str
    path: str
    repeat: int = 0  # when repeat > 0, means line repeated {repeat} more times


@dataclass
class TracebackFrameStack:
    frames: List[TracebackFrame]
    exception_type: str


class TracebackParser:
    FRAME_FILE_PATTERN = re.compile('\s\sFile\s"(.+)",\sline ([0-9]+),\sin\s(.+)')
    FRAME_CODE_LINE_PATTERN = re.compile('\s\s\s\s(.+)')
    FRAME_LOCALS_LINE_PATTERN = re.compile('\s\s\s\s(.+)\s=\s(.+)')
    FRAME_REPEAT_PATTERN = re.compile('^\s\s\[Previous line repeated ([0-9]+) more time(s?)\]$')

    @staticmethod
    def split(arr: List[str], size: int):
        for idx in range(math.floor(len(arr) / size)):
            yield arr[idx * size: idx * size + size]

    def parse_error_flow_stacks(self, stacktrace: str) -> List[ErrorFrameStack]:
        frames: List[ErrorFrame] = []
        stacks: List[ErrorFrameStack] = []

        lines = stacktrace.splitlines()
        line_num = 0
        skip_to_next_traceback = True
        while line_num < len(lines):
            line = lines[line_num]
            if skip_to_next_traceback:
                if line == 'Traceback (most recent call last):':
                    skip_to_next_traceback = False
                    frames = []
                line_num += 1
                continue
            match = self.FRAME_FILE_PATTERN.match(line)
            if match:
                code_line = None
                repeat = 0
                fullpath = match.group(1)
                code_line_num = match.group(2)
                func_name = match.group(3)
                normalize_path = self._file_path_normalizer(fullpath)
                line_num += 1
                line = lines[line_num]
                if bool(self.FRAME_CODE_LINE_PATTERN.match(line)):
                    code_line = line.strip()
                    line_num += 1
                    line = lines[line_num]

                match = self.FRAME_LOCALS_LINE_PATTERN.match("    asd = ffff")
                if match:
                    line_num += 1

                match = self.FRAME_REPEAT_PATTERN.match(line)
                if match:
                    line_num += 1
                    repeat = int(match.group(1))
                frames.append(ErrorFrame(module_name=func_name,
                                         module_path=normalize_path,
                                         excuted_code=code_line,
                                         line_number=code_line_num,
                                         repeat=repeat))
                continue
            if frames:
                # if frames are empty,
                # it means done processing all current traceback details
                # continue until the next traceback
                stacks.append(
                    ErrorFrameStack(frames=frames, exception_type=line.split(':')[0]))
                skip_to_next_traceback = True
            line_num += 1
        return stacks

    @staticmethod
    def _file_path_normalizer(file_path: str) -> str:
        if not path.isabs(file_path):  # case when path start with ./
            if not file_path.startswith('./'):
                return file_path
            file_path = path.relpath(file_path)
            return path.join(path.basename(os.getcwd()), file_path)
        locations = set([site.getusersitepackages()] + site.getsitepackages())
        for prefix in locations:
            if file_path.startswith(prefix):
                normalize_path = file_path[len(prefix) + 1:]
                return normalize_path

        for prefix in sys.path:
            prefix_parent = path.dirname(prefix)
            if file_path.startswith(prefix_parent):
                normalize_path = file_path[len(prefix_parent) + 1:]
                return normalize_path
        return file_path
