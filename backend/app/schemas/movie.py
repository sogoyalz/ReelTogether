from datetime import date

from pydantic import BaseModel, ConfigDict


class MovieBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    franchise: str | None = None
    studios: list[str] = []
    streaming_on: list[str] = []
    directors: list[str] = []
    cast: list[str] = []
    imdb_rating: str | None = None
    rated: str | None = None
    runtime: str | None = None
    rotten_tomatoes: str | None = None
    logo_url: str | None = None


class MovieSummary(MovieBase):
    buzz_score: float
    hype_score: float


class MovieDetail(MovieSummary):
    trailer_url: str | None = None
    trailer_views: int
    social_mentions: int
    google_trends_score: float
    sentiment_score: float
    predicted_opening_weekend_usd: float
    predicted_domestic_total_usd: float
    imdb_id: str | None = None
    box_office: str | None = None
    awards: str | None = None
    metascore: str | None = None
    imdb_votes: str | None = None
    omdb_poster_url: str | None = None
    writers: list[str] = []
    trailer_embed_url: str | None = None
    box_office_history: list[dict[str, str | int]] = []
    backdrops: list[str] = []


class CatalogFacets(BaseModel):
    genres: list[str] = []
    franchises: list[str] = []
    studios: list[str] = []
    streaming: list[str] = []
    statuses: list[str] = []
    years: list[int] = []


class PaginatedMovieSummaries(BaseModel):
    items: list[MovieSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
    facets: CatalogFacets
