from datetime import date

from pydantic import BaseModel


class DiscoveryMovieSummary(BaseModel):
    id: int
    tmdb_id: int
    slug: str
    title: str
    release_date: date
    status: str
    poster_url: str | None = None
    backdrop_url: str | None = None
    overview: str | None = None
    genres: list[str]
    tmdb_popularity: float
    buzz_score: float
    hype_score: float
    franchise: str | None = None
    studios: list[str]
    streaming_on: list[str]
    cast: list[str]
    directors: list[str]


class AutocompleteSuggestion(BaseModel):
    id: int
    slug: str
    title: str
    status: str
    release_date: date


class DashboardBucket(BaseModel):
    label: str
    movie_count: int
    average_hype_score: float


class DiscoveryDashboardResponse(BaseModel):
    trending_by_genre: list[DashboardBucket]
    trending_by_franchise: list[DashboardBucket]
    editorial_collections: dict[str, list[DiscoveryMovieSummary]]
