import time

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = getattr(request.state, "request_id", "unknown")
        started_at = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - started_at
        logger.info(
            "HTTP {} {} returned {} in {:.4f}s (request {})",
            request.method, request.url.path, response.status_code, elapsed, request_id,
        )
        response.headers["X-Process-Time"] = str(elapsed)
        return response
