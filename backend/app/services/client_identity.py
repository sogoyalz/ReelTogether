"""Only the shared-secret proxy may assign a browser rate-limit identity."""
import hashlib
import hmac
import re
import ipaddress
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


def peer_identity(request: Request) -> str:
    """Trust only the proxy-signed canonical peer, never raw forwarded headers."""
    value = request.headers.get('x-movie-peer', '')
    try:
        peer, signature = value.rsplit('.', 1)
        canonical = str(ipaddress.ip_address(peer))
        if canonical != peer or not re.fullmatch('[0-9a-f]{64}', signature):
            raise ValueError('Malformed peer identity')
        expected = hmac.new(settings.PROXY_SHARED_SECRET.encode(), ('peer:' + peer).encode(), hashlib.sha256).hexdigest()
        if settings.PROXY_SHARED_SECRET and hmac.compare_digest(signature, expected):
            return peer
    except ValueError:
        pass
    return request.client.host if request.client else 'unknown'
