import os
import site
from dataclasses import dataclass
from typing import List

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


@dataclass
class TracebackFrameStack:
    frames: List[TracebackFrame]
    exception_type: str


class TracebackParser:

    @staticmethod
    def split(arr: [], size: int):
        for idx in range(math.floor(len(arr) / size)):
            yield arr[idx * size: idx * size + size]

    def error_flow_parser(self, stacktrace: str) -> List[TracebackFrame]:
        lines = stacktrace.splitlines()[1: -1]
        frames = iter(self.split([line.strip() for line in lines], 2))
        error_frames = []
        for frame in frames:
            error_frames.append(self._frame_parser(frame))
        return error_frames

    def parse_error_flow_stacks(self, stacktrace: str) -> List[TracebackFrameStack]:
        frames: List[TracebackFrame] = []
        stacks: List[TracebackFrameStack] = []
        first_frame_line = None
        skip_to_next_traceback = True
        for idx, line in enumerate(stacktrace.splitlines()):
            if skip_to_next_traceback:  # skip lines until next traceback
                if line.startswith('Traceback'):
                    skip_to_next_traceback = False
                    frames = []
                continue

            if line.strip().startswith('File'):  # start a new frame
                first_frame_line = line
            else:
                if first_frame_line:  # in the middle of a frame
                    frames.append(self._frame_parser([first_frame_line, line]))
                    first_frame_line = None
                else:  # last line of a traceback ( exception type)
                    stacks.append(
                        TracebackFrameStack(frames=frames, exception_type=line.split(':')[0]))
                    skip_to_next_traceback = True
        return stacks

    @staticmethod
    def _forward_slash_for_paths(file_path: str) -> str:
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

    def _frame_parser(self, lines: List[str]) -> TracebackFrame:
        split_line = lines[0].split(',')
        fullpath = split_line[0].strip()[6:-1]
        line_num = int(split_line[1].strip()[5:])
        func_name = split_line[2].strip()[3:]
        line = lines[1].strip()
        path = self._forward_slash_for_paths(self._file_path_normalizer(fullpath))
        return TracebackFrame(fullpath=fullpath, line_num=line_num, func_name=func_name, line=line, path=path)
