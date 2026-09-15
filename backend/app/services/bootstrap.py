from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as _models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models.movie import Movie, MovieAnalytics
from app.services.mock_data import build_models


def initialize_database() -> None:
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)


def seed_database_if_empty(db: Session) -> None:
    if settings.tmdb_api_configured:
        return

    existing_movie = db.scalar(select(Movie.id).limit(1))
    if existing_movie is not None:
        return

    for movie, analytics in build_models():
        movie.analytics_snapshots.append(analytics)
        db.add(movie)

    db.commit()


def _seed_missing_movies(db: Session) -> None:
    existing_movies = {
        movie.slug: movie
        for movie in db.scalars(select(Movie)).all()
    }
    existing_movies_by_tmdb_id = {
        movie.tmdb_id: movie
        for movie in existing_movies.values()
    }
    added_or_updated = False

    for movie, analytics in build_models():
        existing = existing_movies.get(movie.slug) or existing_movies_by_tmdb_id.get(movie.tmdb_id)
        if existing is None:
            movie.analytics_snapshots.append(analytics)
            db.add(movie)
            added_or_updated = True
            continue

        _refresh_seed_movie(existing, movie, analytics)
        existing_movies[movie.slug] = existing
        existing_movies_by_tmdb_id[movie.tmdb_id] = existing
        added_or_updated = True

    if added_or_updated:
        db.commit()


def _refresh_seed_movie(existing: Movie, seeded: Movie, seeded_analytics: MovieAnalytics) -> None:
    existing.tmdb_id = seeded.tmdb_id
    existing.slug = seeded.slug
    existing.title = seeded.title
    existing.release_date = seeded.release_date
    existing.status = seeded.status
    existing.poster_url = seeded.poster_url
    existing.backdrop_url = seeded.backdrop_url
    existing.overview = seeded.overview
    existing.genres = seeded.genres
    existing.tmdb_popularity = seeded.tmdb_popularity

    latest_analytics = next(
        (snapshot for snapshot in existing.analytics_snapshots if snapshot.snapshot_label == "latest"),
        None,
    )
    if latest_analytics is None:
        existing.analytics_snapshots.append(seeded_analytics)
        return

    latest_analytics.snapshot_date = seeded_analytics.snapshot_date
    latest_analytics.youtube_views = seeded_analytics.youtube_views
    latest_analytics.youtube_likes = seeded_analytics.youtube_likes
    latest_analytics.youtube_comments = seeded_analytics.youtube_comments
    latest_analytics.google_trends_score = seeded_analytics.google_trends_score
    latest_analytics.x_mentions = seeded_analytics.x_mentions
    latest_analytics.reddit_mentions = seeded_analytics.reddit_mentions
    latest_analytics.sentiment_score = seeded_analytics.sentiment_score
    latest_analytics.sentiment_positive = seeded_analytics.sentiment_positive
    latest_analytics.sentiment_neutral = seeded_analytics.sentiment_neutral
    latest_analytics.sentiment_negative = seeded_analytics.sentiment_negative
    latest_analytics.momentum_score = seeded_analytics.momentum_score
    latest_analytics.buzz_score = seeded_analytics.buzz_score
    latest_analytics.hype_score = seeded_analytics.hype_score
    latest_analytics.predicted_opening_weekend_usd = seeded_analytics.predicted_opening_weekend_usd
    latest_analytics.predicted_domestic_total_usd = seeded_analytics.predicted_domestic_total_usd
    latest_analytics.trailer_url = seeded_analytics.trailer_url
    latest_analytics.last_updated = seeded_analytics.last_updated
