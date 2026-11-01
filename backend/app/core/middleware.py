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
from app.services.client_identity import client_identity, peer_identity
import hashlib


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
        from app.services.operational_metrics import record_request
        record_request(request.method, getattr(route, "path", "unmatched"), response.status_code, (time.perf_counter()-started)*1000)
        logging.getLogger("requests").info(json.dumps({"event": "request", "request_id": request_id,
            "method": request.method, "route": getattr(route, "path", "unmatched"), "status": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2)}))
        if request.url.path.startswith(("/api/auth", "/api/watchlist", "/api/assistant", "/api/movie-nights", "/api/admin")):
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
        try:
            redis_allowed, retry_after = await run_in_threadpool(sliding_window_allow,
                'rate-limit:' + hashlib.sha256(key.encode()).hexdigest(), limit, window_seconds, required=settings.is_production)
            if redis_allowed:
                redis_allowed, retry_after = await run_in_threadpool(sliding_window_allow,
                    'peer-limit:' + hashlib.sha256(peer_identity(request).encode()).hexdigest(),
                    limit * 10, window_seconds, required=settings.is_production)
        except RuntimeError:
            return JSONResponse(status_code=503, content={'detail':'Admission service is temporarily unavailable'}, headers={'Retry-After':'5'})
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


class RequestBodyLimitMiddleware:
    """Bound JSON buffering, including chunked bodies without Content-Length."""
    def __init__(self, app, max_bytes=64 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope.get('method') not in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            return await self.app(scope, receive, send)
        import asyncio
        headers = dict(scope.get('headers', []))
        try:
            declared = int(headers.get(b'content-length', b'0'))
        except ValueError:
            return await JSONResponse({'detail':'Invalid Content-Length'}, status_code=400)(scope, receive, send)
        if declared < 0 or declared > self.max_bytes:
            return await JSONResponse({'detail':'Request body is too large'}, status_code=413)(scope, receive, send)
        body = bytearray()
        deadline = time.monotonic() + 10
        while True:
            try:
                message = await asyncio.wait_for(receive(), timeout=max(0.001, deadline-time.monotonic()))
            except TimeoutError:
                return await JSONResponse({'detail':'Request body timed out'}, status_code=408)(scope, receive, send)
            if message['type'] == 'http.disconnect':
                return
            body.extend(message.get('body', b''))
            if len(body) > self.max_bytes:
                return await JSONResponse({'detail':'Request body is too large'}, status_code=413)(scope, receive, send)
            if not message.get('more_body', False):
                break
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type':'http.request', 'body':bytes(body), 'more_body':False}
            return await receive()
        await self.app(scope, bounded_receive, send)
