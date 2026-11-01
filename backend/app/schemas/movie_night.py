"""Private room responses; never serialize ORM accounts, invites or raw votes."""
from typing import Literal
from pydantic import BaseModel, ConfigDict

State = Literal['lobby', 'voting', 'revealed', 'selected']

class Response(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Ok(Response):
    ok: bool

class RoomIdentity(Response):
    id: str

class Invite(Response):
    invite_token: str

class CreatedRoom(RoomIdentity, Invite):
    pass

class RenewedInvite(Ok, Invite):
    pass

class ListedRoom(RoomIdentity):
    title: str
    state: State
    expired: bool

class RoomList(Response):
    items: list[ListedRoom]

class RoomVersion(Response):
    revision: str
    state: State
    expired: bool

class Member(Response):
    account_id: int
    username: str
    is_host: bool
    complete: bool

class Preferences(Response):
    genres: list[str]
    favorites: list[int]

class Favorite(Response):
    id: int
    title: str

class Film(Favorite):
    slug: str
    poster_url: str | None
    year: int
    genres: list[str]

class Result(Response):
    movie_id: int
    yes: int
    vetoes: int
    eligible: bool
    top_match: bool
    reason: str

class RoomDetail(RoomIdentity, RoomVersion):
    title: str
    is_host: bool
    round_id: int
    expires_at: str
    winner_id: int | None
    members: list[Member]
    preferences: Preferences
    favorite_movies: list[Favorite]
    movies: list[Film]
    my_votes: dict[str, Literal['yes', 'pass', 'veto']]
    results: list[Result]
