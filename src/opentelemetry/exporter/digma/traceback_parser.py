import os
import site
from typing import List

import sys
from os import path

import math


class TracebackParser:

    @staticmethod
    def split(arr: [], size: int):
        for idx in range(math.floor(len(arr) / size)):
            yield arr[idx * size: idx * size + size]

    def error_flow_parser(self, stacktrace: str):
        lines = stacktrace.splitlines()[1: -1]
        frames = iter(self.split([line.strip() for line in lines], 2))
        for frame in frames:
            self._frame_parser(frame)

    @staticmethod
    def _file_path_normalizer(file_path: str):
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

    def _frame_parser(self, lines: List[str]):
        split_line = lines[0].split(',')
        fullpath = split_line[0].strip()[6:-1]
        line_num = int(split_line[1].strip()[5:])
        func_name = split_line[2].strip()[3:]
        line = lines[1].strip()
        path = self._file_path_normalizer(fullpath)
        print(f'full_path: {fullpath}')
        print(f'path: {path}')
        ...