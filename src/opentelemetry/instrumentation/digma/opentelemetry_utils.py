from opentelemetry.trace import SpanKind

from opentelemetry import trace


def opentelemetry_aiohttp_middleware(name: str):
    from aiohttp import web
    tracer = trace.get_tracer(name)
    @web.middleware
    async def middleware(request: web.Request, handler):
        with tracer.start_as_current_span(request.match_info.route.resource.canonical, kind=SpanKind.SERVER):
            return await handler(request)
    return middleware





