"""Explicit response boundaries for private account data."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict
from app.schemas.movie import MovieSummary


class PrivateResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')


class AccountUser(PrivateResponse):
    id: int
    username: str


class AuthState(PrivateResponse):
    user: AccountUser
    csrf_token: str


class Ok(PrivateResponse):
    ok: bool


class RecoveryCode(PrivateResponse):
    recovery_code: str


class RevokedSessions(PrivateResponse):
    revoked: int


class SavedMovie(PrivateResponse):
    movie: MovieSummary
    status: Literal['planned', 'watched']
    added_at: datetime


class WatchlistPage(PrivateResponse):
    items: list[SavedMovie]
    total: int
    page: int
    total_pages: int


class ExportUser(PrivateResponse):
    username: str
    created_at: datetime


class ExportSavedMovie(PrivateResponse):
    movie_id: int
    title: str
    slug: str
    status: Literal['planned', 'watched']
    added_at: datetime


class ExportFeedback(PrivateResponse):
    movie_id: int
    preference: Literal['like', 'dislike']


class ExportMovieNight(PrivateResponse):
    id: str
    title: str
    state: str
    hosted_by_you: bool
    genres: list[str]
    favorites: list[int]
    winner_id: int | None


class ExportVote(PrivateResponse):
    room_id: str
    movie_id: int
    choice: str


class AccountExport(PrivateResponse):
    format_version: Literal[1]
    account: ExportUser
    watchlist: list[ExportSavedMovie]
    feedback: list[ExportFeedback]
    movie_nights: list[ExportMovieNight]
    votes: list[ExportVote]
