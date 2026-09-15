from datetime import date, datetime

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
    data_quality: str = "medium"
    field_sources: dict[str, str] = {}
    last_verified_at: datetime | None = None
    warnings: list[str] = []


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
    forecast_is_public: bool = True
    forecast_status: str = "public"
    forecast_note: str = ""
    engagement_metrics_are_estimated: bool = True
    engagement_metrics_note: str = ""
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
    wikipedia_summary: str | None = None
    wikipedia_url: str | None = None
    wikipedia_categories: list[str] = []
    wikidata_id: str | None = None
    wikidata_url: str | None = None
    wikidata_label: str | None = None
    wikidata_description: str | None = None
    wikidata_instance_of: list[str] = []
    wikidata_genres: list[str] = []
    wikidata_countries: list[str] = []


class CatalogFacets(BaseModel):
    genres: list[str] = []
    franchises: list[str] = []
    studios: list[str] = []
    directors: list[str] = []
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
