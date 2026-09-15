from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock

from fastapi import Request
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.services.redis_store import sliding_window_allow
from app.services.client_identity import client_identity


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        started = time.perf_counter()
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception as error:
            # Never log request bodies, cookies, query strings, or exception messages.
            logging.getLogger("requests").error(json.dumps({"event": "request_failed", "request_id": request_id, "error_type": type(error).__name__}))
            response = JSONResponse(status_code=500, content={"detail": "An unexpected error occurred", "request_id": request_id})
        route = request.scope.get("route")
        logging.getLogger("requests").info(json.dumps({"event": "request", "request_id": request_id,
            "method": request.method, "route": getattr(route, "path", "unmatched"), "status": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2)}))
        if request.url.path.startswith(("/api/auth", "/api/watchlist", "/api/assistant", "/api/movie-nights")):
            response.headers["Cache-Control"] = "private, no-store"
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

        key = client_identity(request)
        now = time.monotonic()
        window_seconds = 60
        limit = settings.RATE_LIMIT_REQUESTS_PER_MINUTE + settings.RATE_LIMIT_BURST_REQUESTS
        redis_allowed, retry_after = await run_in_threadpool(sliding_window_allow, f"rate-limit:{key}", limit, window_seconds)
        if not redis_allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        with self._lock:
            for stale in [k for k, v in self._requests.items() if not v or now - v[-1] > window_seconds]:
                del self._requests[stale]
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
