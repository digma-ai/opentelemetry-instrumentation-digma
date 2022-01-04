class ExceptionWithParams:
    def __init__(self) -> None:
        pass
    def throw_exception(self, arg1,arg2):
        raise Exception('An exception with args was thrown')