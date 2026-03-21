from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import settings


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.ENABLE_RATE_LIMIT or not request.url.path.startswith(settings.API_V1_PREFIX):
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        key = f"{client_host}:{request.url.path}"
        now = time.monotonic()
        window_seconds = 60
        limit = settings.RATE_LIMIT_REQUESTS_PER_MINUTE + settings.RATE_LIMIT_BURST_REQUESTS

        with self._lock:
            entries = self._requests[key]
            while entries and now - entries[0] > window_seconds:
                entries.popleft()
            if len(entries) >= limit:
                retry_after = max(1, int(window_seconds - (now - entries[0])))
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after_seconds": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            entries.append(now)

        return await call_next(request)
