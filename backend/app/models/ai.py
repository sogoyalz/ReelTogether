from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class MovieDiscussion(Base):
    __tablename__ = "movie_discussions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(128), nullable=True)
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    movie = relationship("Movie", back_populates="discussions")


class MovieSentimentSnapshot(Base):
    __tablename__ = "movie_sentiment_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    positive_count: Mapped[int] = mapped_column(Integer, default=0)
    neutral_count: Mapped[int] = mapped_column(Integer, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    model_version: Mapped[str] = mapped_column(String(64), default="bootstrap-v1")

    movie = relationship("Movie", back_populates="sentiment_snapshots")


class MoviePredictionSnapshot(Base):
    __tablename__ = "movie_prediction_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    predicted_opening_weekend_usd: Mapped[float] = mapped_column(Float, default=0.0)
    predicted_domestic_total_usd: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    feature_version: Mapped[str] = mapped_column(String(64), default="bootstrap-v1")
    model_version: Mapped[str] = mapped_column(String(64), default="rule-bootstrap-v1")

    movie = relationship("Movie", back_populates="prediction_snapshots")


class MovieFeatureSnapshot(Base):
    __tablename__ = "movie_feature_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    release_days_until: Mapped[int] = mapped_column(Integer, default=0)
    trailer_views: Mapped[int] = mapped_column(Integer, default=0)
    likes_to_views_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    comments_to_views_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    reddit_mentions: Mapped[int] = mapped_column(Integer, default=0)
    social_mentions: Mapped[int] = mapped_column(Integer, default=0)
    tmdb_popularity: Mapped[float] = mapped_column(Float, default=0.0)
    imdb_rating: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    feature_version: Mapped[str] = mapped_column(String(64), default="bootstrap-v1")

    movie = relationship("Movie", back_populates="feature_snapshots")


class MovieSummarySnapshot(Base):
    __tablename__ = "movie_summary_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    audience_summary: Mapped[str] = mapped_column(Text)
    critic_summary: Mapped[str] = mapped_column(Text)
    key_themes: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(64), default="editorial-bootstrap-v1")

    movie = relationship("Movie", back_populates="summary_snapshots")


class ReviewSentiment(Base):
    __tablename__ = "review_sentiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    author: Mapped[str] = mapped_column(String(255), index=True)
    content_snippet: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_label: Mapped[str] = mapped_column(String(32), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(32), index=True)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    movie = relationship("Movie", back_populates="review_sentiments")
