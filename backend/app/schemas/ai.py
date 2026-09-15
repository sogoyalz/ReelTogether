from datetime import datetime

from pydantic import BaseModel, Field


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

    opening_weekend_low_usd: float = 0
    opening_weekend_high_usd: float = 0
    domestic_total_low_usd: float = 0
    domestic_total_high_usd: float = 0
    forecast_is_public: bool = False
    forecast_status: str = "unavailable"
    forecast_note: str = ""
    methodology: str = ""
    feature_importance: list[dict] = Field(default_factory=list)


class MovieSummarySnapshotResponse(BaseModel):
    movie_id: int
    snapshot_at: datetime
    audience_summary: str
    critic_summary: str
    key_themes: list[str]
    model_version: str


class PublicOpinionSourceBreakdown(BaseModel):
    source: str
    item_count: int
    average_sentiment: float


class PublicOpinionResponse(BaseModel):
    overall_summary: str
    positive_count: int
    neutral_count: int
    negative_count: int
    average_sentiment: float
    top_themes: list[str]
    source_breakdown: list[PublicOpinionSourceBreakdown]
    highlighted_quotes: list[str]


class MovieAIOverviewResponse(BaseModel):
    sentiment: MovieSentimentSnapshotResponse
    prediction: MoviePredictionSnapshotResponse
    summary: MovieSummarySnapshotResponse
    public_opinion: PublicOpinionResponse
    discussions: list[DiscussionItem]
    critic_vs_audience: dict
