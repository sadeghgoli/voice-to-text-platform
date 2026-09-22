from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

log = structlog.get_logger()


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("api.request_failed", method=request.method, path=request.url.path)
            raise
        finally:
            structlog.contextvars.clear_contextvars()
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger = log.debug if request.url.path.startswith("/health") else log.info
        logger("api.request", method=request.method, path=request.url.path, status=response.status_code, duration_ms=duration_ms)
        response.headers["X-Request-ID"] = request_id
        return response
