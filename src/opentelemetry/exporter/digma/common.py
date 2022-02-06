import os

IGNORE_LIST = [os.path.join('opentelemetry', 'trace', '__init__.py'),
               os.path.join('opentelemetry', 'sdk', 'trace', '__init__.py')]

BUILT_IN_EXCEPTIONS = [
     "SystemExit",  "KeyboardInterrupt", "GeneratorExit", "StopIteration", "StopAsyncIteration", "ArithmeticError",
     "FloatingPointError",  "OverflowError", "ZeroDivisionError", "AssertionError", "AttributeError", "BufferError",
     "EOFError", "ImportError", "ModuleNotFoundError", "LookupError", "IndexError", "KeyError", "MemoryError",
     "NameError", "UnboundLocalError", "BlockingIOError", "ChildProcessError",
      "ConnectionResetError", "FileExistsError",
     "FileNotFoundError", "InterruptedError", "IsADirectoryError", "NotADirectoryError", "PermissionError",
     "ProcessLookupError", "ReferenceError", "RuntimeError", "NotImplementedError", "RecursionError",
     "SyntaxError", "IndentationError", "TabError", "SystemError", "TypeError", "ValueError", "UnicodeError",
     "UnicodeDecodeError", "UnicodeEncodeError", "UnicodeTranslateError"
]

def is_builtin_exception(exception):
    return exception in BUILT_IN_EXCEPTIONS


