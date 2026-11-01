from datetime import date, datetime

from pydantic import BaseModel


from app.schemas.movie import MovieSummary as DiscoveryMovieSummary


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


class DashboardStats(BaseModel):
    tracked_movies: int
    average_hype_score: float
    average_buzz_score: float


class DashboardResponse(BaseModel):
    updated_at: datetime
    trending: list[DiscoveryMovieSummary]
    most_hyped: list[DiscoveryMovieSummary]
    stats: DashboardStats


class HomePagePayload(BaseModel):
    trending: list[DiscoveryMovieSummary]
    upcoming: list[DiscoveryMovieSummary]
    released: list[DiscoveryMovieSummary]
    dashboard: DashboardResponse
