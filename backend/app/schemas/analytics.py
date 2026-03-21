from datetime import date, datetime

from pydantic import BaseModel


class SentimentBreakdown(BaseModel):
    positive: int
    neutral: int
    negative: int


class MovieAnalyticsResponse(BaseModel):
    movie_id: int
    movie_title: str
    snapshot_date: date
    youtube_views: int
    youtube_likes: int
    youtube_comments: int
    google_trends_score: float
    x_mentions: int
    reddit_mentions: int
    social_mentions: int
    sentiment_score: float
    sentiment_breakdown: SentimentBreakdown
    buzz_score: float
    hype_score: float
    predicted_opening_weekend_usd: float
    predicted_domestic_total_usd: float
    trailer_url: str | None = None
    updated_at: datetime
    score_breakdown: "ScoreBreakdown"


class AnalyticsHistoryPoint(BaseModel):
    snapshot_date: date
    buzz_score: float
    hype_score: float
    youtube_views: int
    social_mentions: int
    google_trends_score: float


class AnalyticsHistoryResponse(BaseModel):
    movie_id: int
    movie_title: str
    points: list[AnalyticsHistoryPoint]


class ScoreBreakdown(BaseModel):
    youtube_interest: float
    search_interest: float
    social_buzz: float
    sentiment: float
    momentum: float
    release_proximity: float


class ComparisonEntry(BaseModel):
    movie_id: int
    slug: str
    title: str
    release_date: date
    status: str
    buzz_score: float
    hype_score: float
    youtube_views: int
    social_mentions: int
    google_trends_score: float
    sentiment_score: float
    predicted_opening_weekend_usd: float
    predicted_domestic_total_usd: float
    tmdb_popularity: float
    imdb_rating: str | None = None
    rotten_tomatoes: str | None = None
    runtime: str | None = None
    franchise: str | None = None
    streaming_on: list[str] = []
    audience_sentiment: float | None = None
    prediction_confidence: float | None = None
    key_themes: list[str] = []


class CompareMoviesResponse(BaseModel):
    compared_at: datetime
    items: list[ComparisonEntry]


class RefreshAnalyticsResponse(BaseModel):
    refreshed_movies: int
    skipped_movies: int
    failed_movies: int
    skipped_reasons: list[str]
    failed_reasons: list[str]
