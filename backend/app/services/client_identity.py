"""Only the shared-secret proxy may assign a browser rate-limit identity."""
import hashlib
import hmac
import re
from fastapi import Request
from app.core.config import settings


def client_identity(request: Request) -> str:
    token = request.headers.get("x-movie-client", "")
    if settings.PROXY_SHARED_SECRET and re.fullmatch(r"[0-9a-fA-F-]{36}\.[0-9a-f]{64}", token):
        identity, signature = token.split(".")
        expected = hmac.new(settings.PROXY_SHARED_SECRET.encode(), identity.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected):
            return "browser:" + identity
    return "ip:" + (request.client.host if request.client else "unknown")
