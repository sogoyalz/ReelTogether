"""Password verification and revocable, opaque browser sessions."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from threading import Lock, BoundedSemaphore
from time import monotonic

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.models.account import Account, LoginSession
from app.services.cache import ExpiringMap
from app.services.client_identity import client_identity

COOKIE = "movie-session"
SESSION_SECONDS = 7 * 24 * 60 * 60
passwords = PasswordHasher()
_password_slots = BoundedSemaphore(2)
_dummy_hash = passwords.hash(secrets.token_urlsafe(32))
_attempts = ExpiringMap(ttl_seconds=3600, max_entries=4096)
_attempt_lock = Lock()


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def token_digest(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


def require_same_origin(request: Request):
    origin = request.headers.get("origin")
    if origin not in settings.CORS_ORIGINS:
        raise HTTPException(403, "Request origin is not allowed")


def throttle_auth(request: Request, username: str):
    # Signed browser identity separates users behind the frontend proxy.
    # The username limit remains independent, including across new cookies.
    identity = client_identity(request)
    timestamp = monotonic()
    with _attempt_lock:
        pending = {}
        for key, limit, seconds in [(identity, 60, 3600), ("user:" + username, 10, 600)]:
            entries = [t for t in _attempts.get(key, []) if timestamp - t < seconds]
            if len(entries) >= limit:
                raise HTTPException(429, "Too many authentication attempts; try again later", headers={"Retry-After": str(max(1, int(seconds - (timestamp - entries[0])) + 1))})
            entries.append(timestamp)
            pending[key] = entries
        for key, entries in pending.items():
            _attempts[key] = entries


def verify_password(account: Account | None, password: str):
    try:
        with _password_slots:
            valid = passwords.verify(account.password_hash if account else _dummy_hash, password)
    except (VerificationError, InvalidHashError):
        return False
    return bool(account and valid)


def create_session(db: Session, account: Account, request: Request, response: Response):
    old_token = request.cookies.get(COOKIE)
    if old_token:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == token_digest(old_token)))
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= now()))
    # Limit retained sessions per account.
    retained = list(db.scalars(select(LoginSession).where(LoginSession.account_id == account.id).order_by(LoginSession.expires_at.desc())))
    for expired in retained[9:]:
        db.delete(expired)
    token = secrets.token_urlsafe(32)
    session = LoginSession(token_hash=token_digest(token), account_id=account.id,
                           csrf_token=secrets.token_hex(32), expires_at=now() + timedelta(seconds=SESSION_SECONDS))
    db.add(session)
    db.commit()
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True,
                        secure=settings.is_production, samesite="strict", path="/api")
    response.headers["Cache-Control"] = "private, no-store"
    return {"user": {"id": account.id, "username": account.username}, "csrf_token": session.csrf_token}


def current_session(request: Request, db: Session = Depends(get_db)) -> LoginSession:
    token = request.cookies.get(COOKIE, "")
    session = db.get(LoginSession, token_digest(token)) if token else None
    if session is None or session.expires_at <= now():
        raise HTTPException(401, "Sign in to use your watchlist")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        require_same_origin(request)
        if not hmac.compare_digest(request.headers.get("x-csrf-token", ""), session.csrf_token):
            raise HTTPException(403, "Invalid CSRF token; reload and try again")
    return session


def hash_password(password: str):
    with _password_slots:
        return passwords.hash(password)
