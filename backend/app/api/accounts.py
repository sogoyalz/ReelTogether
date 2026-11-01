from app.schemas.identifiers import MovieId
import secrets
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.services.movie_serialization import serialize_summary as _serialize_summary_fast
from app.core.config import settings
from app.db.session import get_db
from app.models.account import Account, LoginSession, WatchlistEntry
from app.models.movie import Movie
from app.repositories.movies import summary_analytics_option
from app.services.authentication import COOKIE, create_session, current_session, hash_password, passwords, require_same_origin, throttle_auth, token_digest, verify_password, now

from app.schemas.account import AuthState, Ok, RecoveryCode, RevokedSessions, WatchlistPage, AccountExport

router = APIRouter()


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-z0-9_]+$")
    password: str = Field(min_length=12, max_length=128)
    @field_validator("username", mode="before")
    @classmethod
    def normalize(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class WatchStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["planned", "watched"]


@router.post("/auth/register", status_code=201, response_model=AuthState)
def register(payload: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    require_same_origin(request)
    throttle_auth(request, payload.username)
    account = Account(username=payload.username, password_hash=hash_password(payload.password))
    db.add(account)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Username is unavailable") from None
    return create_session(db, account, request, response)


@router.post("/auth/login", response_model=AuthState)
def login(payload: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    require_same_origin(request)
    throttle_auth(request, payload.username)
    account = db.scalar(select(Account).where(Account.username == payload.username))
    if not verify_password(account, payload.password):
        raise HTTPException(401, "Invalid username or password")
    verified_hash = account.password_hash
    next_hash = hash_password(payload.password) if passwords.check_needs_rehash(verified_hash) else verified_hash
    # A conditional write rechecks the credential and holds the account write
    # lock through session commit. Recovery either precedes it (reject login)
    # or follows it (and deletes the newly created session).
    changed = db.execute(update(Account).where(
        Account.id == account.id, Account.password_hash == verified_hash,
    ).values(password_hash=next_hash))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(401, "Credentials changed; sign in again")
    return create_session(db, account, request, response)


@router.get("/auth/me", response_model=AuthState)
def me(response: Response, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    account = db.get(Account, session.account_id)
    if account is None:
        raise HTTPException(401, "Account no longer exists")
    response.headers["Cache-Control"] = "private, no-store"
    return {"user": {"id": account.id, "username": account.username}, "csrf_token": session.csrf_token}


@router.post("/auth/logout", response_model=Ok)
def logout(response: Response, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    db.delete(session)
    db.commit()
    response.delete_cookie(COOKIE, path="/api", httponly=True, secure=settings.is_production, samesite="strict")
    response.headers["Cache-Control"] = "private, no-store"
    return {"ok": True}


@router.get("/watchlist", response_model=WatchlistPage)
def watchlist(response: Response, page: int = Query(1, ge=1), page_size: int = Query(24, ge=1, le=48), session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    predicate = WatchlistEntry.account_id == session.account_id
    total = db.scalar(select(func.count()).select_from(WatchlistEntry).where(predicate)) or 0
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    rows = db.execute(
        select(WatchlistEntry, Movie)
        .join(Movie, Movie.id == WatchlistEntry.movie_id)
        .options(summary_analytics_option())
        .where(predicate)
        .order_by(WatchlistEntry.added_at.desc(), WatchlistEntry.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "items": [{"movie": _serialize_summary_fast(movie), "status": entry.status, "added_at": entry.added_at} for entry, movie in rows],
        "total": total, "page": page, "total_pages": total_pages,
    }



@router.get("/watchlist/{movie_id}")
def watchlist_status(movie_id: MovieId, response: Response, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    entry = db.scalar(select(WatchlistEntry).where(WatchlistEntry.account_id == session.account_id, WatchlistEntry.movie_id == movie_id))
    response.headers["Cache-Control"] = "private, no-store"
    return {"saved": entry is not None, "status": entry.status if entry else None}


@router.put("/watchlist/{movie_id}")
def save_movie(movie_id: MovieId, response: Response, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    if db.get(Movie, movie_id) is None:
        raise HTTPException(404, "Movie not found")
    entry = db.scalar(select(WatchlistEntry).where(WatchlistEntry.account_id == session.account_id, WatchlistEntry.movie_id == movie_id))
    if entry is None:
        db.add(WatchlistEntry(account_id=session.account_id, movie_id=movie_id, status="planned"))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # Concurrent duplicate saves are idempotent; never suppress another failure.
            existing = db.scalar(select(WatchlistEntry.id).where(WatchlistEntry.account_id == session.account_id, WatchlistEntry.movie_id == movie_id))
            if existing is None:
                raise
    response.headers["Cache-Control"] = "private, no-store"
    return {"saved": True}


@router.patch("/watchlist/{movie_id}")
def update_status(movie_id: MovieId, payload: WatchStatus, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    entry = db.scalar(select(WatchlistEntry).where(WatchlistEntry.account_id == session.account_id, WatchlistEntry.movie_id == movie_id))
    if entry is None:
        raise HTTPException(404, "Movie is not in your watchlist")
    entry.status = payload.status
    db.commit()
    return {"status": entry.status}


@router.delete("/watchlist/{movie_id}")
def remove_movie(movie_id: MovieId, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    db.execute(delete(WatchlistEntry).where(WatchlistEntry.account_id == session.account_id, WatchlistEntry.movie_id == movie_id))
    db.commit()
    return {"saved": False}


class RecoverySetup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=12, max_length=128)


class RecoveryReset(Credentials):
    recovery_code: str = Field(min_length=32, max_length=128)


@router.post("/auth/recovery-code", response_model=RecoveryCode)
def recovery_code(payload: RecoverySetup, request: Request, response: Response, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    account = db.get(Account, session.account_id)
    throttle_auth(request, account.username if account else "unknown")
    if not verify_password(account, payload.password):
        raise HTTPException(401, "Invalid password")
    code = secrets.token_urlsafe(32)
    changed = db.execute(update(Account).where(Account.id == account.id, Account.password_hash == account.password_hash).values(recovery_hash=token_digest(code)))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Account changed; sign in again")
    db.commit()
    response.headers["Cache-Control"] = "private, no-store"
    return {"recovery_code": code}


@router.post("/auth/recover", response_model=Ok)
def recover(payload: RecoveryReset, request: Request, response: Response, db: Session = Depends(get_db)):
    require_same_origin(request)
    throttle_auth(request, payload.username)
    # Hash before lookup so unknown usernames do not take a distinct fast path.
    password_hash = hash_password(payload.password)
    recovered = db.execute(update(Account).where(
        Account.username == payload.username,
        Account.recovery_hash == token_digest(payload.recovery_code),
    ).values(password_hash=password_hash, recovery_hash=None).returning(Account.id)).scalar_one_or_none()
    if recovered is None:
        db.rollback()
        raise HTTPException(400, "Invalid username or recovery code")
    # The conditional UPDATE consumes the code atomically, including concurrent requests.
    db.execute(delete(LoginSession).where(LoginSession.account_id == recovered))
    db.commit()
    response.delete_cookie(COOKIE, path="/api", httponly=True, secure=settings.is_production, samesite="strict")
    response.headers["Cache-Control"] = "private, no-store"
    return {"ok": True}


class PasswordChange(RecoverySetup):
    new_password: str = Field(min_length=12, max_length=128)


def _reauthenticate(payload: RecoverySetup, request: Request, session: LoginSession, db: Session):
    account = db.get(Account, session.account_id)
    throttle_auth(request, account.username if account else "unknown")
    if not verify_password(account, payload.password):
        raise HTTPException(401, "Invalid password")
    # Serialize sensitive changes against login/recovery on both supported databases.
    changed = db.execute(update(Account).where(Account.id == account.id,
        Account.password_hash == account.password_hash).values(password_hash=account.password_hash))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Account changed; sign in again")
    return account


@router.post("/auth/password", response_model=AuthState)
def change_password(payload: PasswordChange, request: Request, response: Response,
                    session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    account = _reauthenticate(payload, request, session, db)
    account.password_hash = hash_password(payload.new_password)
    account.recovery_hash = None
    db.execute(delete(LoginSession).where(LoginSession.account_id == account.id))
    return create_session(db, account, request, response)


@router.post("/auth/revoke-other-sessions", response_model=RevokedSessions)
def revoke_other_sessions(payload: RecoverySetup, request: Request, response: Response,
                          session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    account = _reauthenticate(payload, request, session, db)
    removed = db.execute(delete(LoginSession).where(LoginSession.account_id == account.id,
        LoginSession.token_hash != session.token_hash)).rowcount
    db.commit()
    response.headers["Cache-Control"] = "private, no-store"
    return {"revoked": removed}


@router.get("/auth/export", response_model=AccountExport)
def export_account(response: Response, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    from app.models.account import MovieFeedback
    from app.models.movie_night import MovieNight, NightMember, NightVote
    account = db.get(Account, session.account_id)
    saved = db.execute(select(WatchlistEntry, Movie.title, Movie.slug).join(Movie).where(
        WatchlistEntry.account_id == session.account_id)).all()
    preferences = list(db.scalars(select(MovieFeedback).where(MovieFeedback.account_id == session.account_id)))
    memberships = db.execute(select(NightMember, MovieNight).join(MovieNight).where(
        NightMember.account_id == session.account_id)).all()
    votes = list(db.scalars(select(NightVote).where(NightVote.account_id == session.account_id)))
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Content-Disposition"] = 'attachment; filename="reeltogether-account.json"'
    return {"format_version": 1, "account": {"username": account.username, "created_at": account.created_at},
        "watchlist": [{"movie_id": entry.movie_id, "title": title, "slug": slug, "status": entry.status, "added_at": entry.added_at} for entry, title, slug in saved],
        "feedback": [{"movie_id": entry.movie_id, "preference": entry.preference} for entry in preferences],
        "movie_nights": [{"id": room.id, "title": room.title, "state": room.state, "hosted_by_you": room.host_id == account.id,
            "genres": member.genres, "favorites": member.favorites, "winner_id": room.winner_id} for member, room in memberships],
        "votes": [{"room_id": vote.room_id, "movie_id": vote.movie_id, "choice": vote.choice} for vote in votes]}


@router.post("/auth/delete-account", response_model=Ok)
def delete_account(payload: RecoverySetup, request: Request, response: Response,
                   session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    account = _reauthenticate(payload, request, session, db)
    from app.models.account import AccountErasure
    from app.services.erasure_ledger import publish_pending
    erasure_key = account.erasure_key
    db.add(AccountErasure(erasure_key=erasure_key,requested_at=now()))
    db.execute(delete(Account).where(Account.id == account.id))
    db.commit()
    try:
        publish_pending(db)
        if settings.is_production and db.get(AccountErasure, erasure_key).exported_at is None:
            raise RuntimeError('Erasure export is pending')
    except (OSError, RuntimeError):
        # The erasure already committed. The durable outbox is retried by the
        # backup worker; do not claim a recoverable receipt was published.
        raise HTTPException(503,'Account deleted; recovery receipt is pending. Contact the operator if this persists.',headers={'Retry-After':'5'}) from None
    response.delete_cookie(COOKIE, path="/api", httponly=True, secure=settings.is_production, samesite="strict")
    response.headers["Cache-Control"] = "private, no-store"
    return {"ok": True}
