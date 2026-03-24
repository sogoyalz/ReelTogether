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


class PredictionFeatureImportanceResponse(BaseModel):
    label: str
    value: float
    impact_score: float
    direction: str
    explanation: str


class MoviePredictionSnapshotResponse(BaseModel):
    movie_id: int
    snapshot_at: datetime
    predicted_opening_weekend_usd: float
    predicted_domestic_total_usd: float
    confidence_score: float
    opening_weekend_low_usd: float
    opening_weekend_high_usd: float
    domestic_total_low_usd: float
    domestic_total_high_usd: float
    methodology: str
    feature_version: str
    model_version: str
    feature_importance: list["PredictionFeatureImportanceResponse"]


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


class ReviewPerspectiveResponse(BaseModel):
    label: str
    item_count: int
    sentiment_score: float
    summary: str
    top_themes: list[str]
    positive_drivers: list[str]
    negative_drivers: list[str]
    highlighted_quotes: list[str]


class ThemeSignalResponse(BaseModel):
    theme: str
    critic_weight: float
    audience_weight: float
    gap: float


class CriticAudienceComparisonResponse(BaseModel):
    critics: ReviewPerspectiveResponse
    audience: ReviewPerspectiveResponse
    consensus_themes: list[str]
    divergence_themes: list[str]
    alignment_score: float
    theme_signals: list[ThemeSignalResponse]


class MovieAIOverviewResponse(BaseModel):
    sentiment: MovieSentimentSnapshotResponse
    prediction: MoviePredictionSnapshotResponse
    summary: MovieSummarySnapshotResponse
    public_opinion: PublicOpinionResponse
    critic_vs_audience: CriticAudienceComparisonResponse
    discussions: list[DiscussionItem]
