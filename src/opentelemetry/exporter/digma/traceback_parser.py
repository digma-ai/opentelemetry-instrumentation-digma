import os
import re
import site
from dataclasses import dataclass
from typing import List, Tuple

import sys
from os import path

import math


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
    FRAME_FILE_PATTERN = '\s\sFile\s".*",\sline [0-9]+,\sin\s.*'
    FRAME_CODE_LINE_PATTERN = '(\s\s\s\s.*).+'
    FRAME_LOCALS_LINE_PATTERN = '\s\s\s\s.*\s=\s.*'
    FRAME_REPEAT_PATTERN = '^\s\s\[Previous line repeated ([0-9]+) more time(s?)\]$'

    @staticmethod
    def split(arr: List[str], size: int):
        for idx in range(math.floor(len(arr) / size)):
            yield arr[idx * size: idx * size + size]

    def parse_error_flow_stacks(self, stacktrace: str) -> List[TracebackFrameStack]:
        frames: List[TracebackFrame] = []
        stacks: List[TracebackFrameStack] = []

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
            if bool(re.match(self.FRAME_FILE_PATTERN, line)):
                code_line = None
                repeat = 0
                fullpath, func_name, code_line_num, normalize_path = self.file_line_parser(line)
                line_num += 1
                line = lines[line_num]
                if bool(re.match(self.FRAME_CODE_LINE_PATTERN, line)):
                    code_line = line.strip()
                    line_num += 1
                    line = lines[line_num]

                if bool(re.match(self.FRAME_CODE_LINE_PATTERN, line)):
                    line_num += 1

                match = re.search(self.FRAME_REPEAT_PATTERN, line)
                if match:
                    line_num += 1
                    repeat = int(match.group(1))
                frames.append(TracebackFrame(fullpath=fullpath,
                                             line_num=code_line_num,
                                             func_name=func_name,
                                             line=code_line,
                                             path=normalize_path,
                                             repeat=repeat))
                continue
            if frames:
                # if frames are empty,
                # it means done processing all current traceback details
                # continue until the next traceback
                stacks.append(
                    TracebackFrameStack(frames=frames, exception_type=line.split(':')[0]))
                skip_to_next_traceback = True
            line_num += 1
        return stacks

    def file_line_parser(self, line) -> Tuple[str, str, int, str]:
        split_line = line.split(',')
        fullpath = split_line[0].strip()[6:-1]
        line_num = int(split_line[1].strip()[5:])
        func_name = split_line[2].strip()[3:]
        normalize_path = self._forward_slash_for_paths(self._file_path_normalizer(fullpath))
        return fullpath, func_name, line_num, normalize_path

    @staticmethod
    def _forward_slash_for_paths(file_path: str) -> str:  # todo: shay why cannot we use os definitions?
        return file_path.replace('\\', '/')

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
