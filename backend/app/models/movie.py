from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    release_date: Mapped[Date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(64), default="upcoming")
    poster_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    backdrop_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    genres: Mapped[list[str]] = mapped_column(JSON, default=list)
    tmdb_popularity: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    analytics_snapshots: Mapped[list["MovieAnalytics"]] = relationship(
        "MovieAnalytics",
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    discussions: Mapped[list["MovieDiscussion"]] = relationship(
        "MovieDiscussion",
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    sentiment_snapshots: Mapped[list["MovieSentimentSnapshot"]] = relationship(
        "MovieSentimentSnapshot",
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    prediction_snapshots: Mapped[list["MoviePredictionSnapshot"]] = relationship(
        "MoviePredictionSnapshot",
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    feature_snapshots: Mapped[list["MovieFeatureSnapshot"]] = relationship(
        "MovieFeatureSnapshot",
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    summary_snapshots: Mapped[list["MovieSummarySnapshot"]] = relationship(
        "MovieSummarySnapshot",
        back_populates="movie",
        cascade="all, delete-orphan",
    )


class MovieAnalytics(Base):
    __tablename__ = "movie_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), index=True)
    snapshot_label: Mapped[str] = mapped_column(String(64), default="latest")
    snapshot_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    youtube_views: Mapped[int] = mapped_column(Integer, default=0)
    youtube_likes: Mapped[int] = mapped_column(Integer, default=0)
    youtube_comments: Mapped[int] = mapped_column(Integer, default=0)
    google_trends_score: Mapped[float] = mapped_column(Float, default=0.0)
    x_mentions: Mapped[int] = mapped_column(Integer, default=0)
    reddit_mentions: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_positive: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_neutral: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_negative: Mapped[int] = mapped_column(Integer, default=0)
    momentum_score: Mapped[float] = mapped_column(Float, default=0.0)
    buzz_score: Mapped[float] = mapped_column(Float, default=0.0)
    hype_score: Mapped[float] = mapped_column(Float, default=0.0)
    predicted_opening_weekend_usd: Mapped[float] = mapped_column(Float, default=0.0)
    predicted_domestic_total_usd: Mapped[float] = mapped_column(Float, default=0.0)
    trailer_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    movie: Mapped["Movie"] = relationship("Movie", back_populates="analytics_snapshots")
