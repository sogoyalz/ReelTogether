from datetime import datetime

from pydantic import BaseModel


class DiscussionItem(BaseModel):
    source: str
    title: str
    body: str
    author: str | None = None
    engagement_score: float
    created_at: datetime
    url: str | None = None


class MovieSentimentSnapshotResponse(BaseModel):
    movie_id: int
    snapshot_at: datetime
    positive_count: int
    neutral_count: int
    negative_count: int
    sentiment_score: float
    sample_size: int
    model_version: str


class MoviePredictionSnapshotResponse(BaseModel):
    movie_id: int
    snapshot_at: datetime
    predicted_opening_weekend_usd: float
    predicted_domestic_total_usd: float
    confidence_score: float
    feature_version: str
    model_version: str


class MovieSummarySnapshotResponse(BaseModel):
    movie_id: int
    snapshot_at: datetime
    audience_summary: str
    critic_summary: str
    key_themes: list[str]
    model_version: str


class MovieAIOverviewResponse(BaseModel):
    sentiment: MovieSentimentSnapshotResponse
    prediction: MoviePredictionSnapshotResponse
    summary: MovieSummarySnapshotResponse
    discussions: list[DiscussionItem]
