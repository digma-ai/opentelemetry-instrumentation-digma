import traceback


def get_traceback_with_locals(ex: Exception):
    if not ex:
        return None

    st = list(iter(traceback.TracebackException.from_exception(
        ex, limit=10, capture_locals=True).format()))

    full_trace = str.join('\n', st)

    return full_trace
