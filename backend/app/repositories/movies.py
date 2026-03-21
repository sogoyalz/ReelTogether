from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.movie import Movie, MovieAnalytics


def _latest_analytics_option():
    return selectinload(Movie.analytics_snapshots)


def list_movies(db: Session) -> list[Movie]:
    statement = select(Movie).options(_latest_analytics_option()).order_by(Movie.title.asc())
    return list(db.scalars(statement).unique().all())


def list_trending_movies(db: Session, limit: int = 6) -> list[Movie]:
    statement = (
        select(Movie)
        .join(MovieAnalytics)
        .options(_latest_analytics_option())
        .where(MovieAnalytics.snapshot_label == "latest")
        .order_by(MovieAnalytics.buzz_score.desc(), Movie.title.asc())
        .limit(limit)
    )
    return list(db.scalars(statement).unique().all())


def list_upcoming_movies(db: Session, today: date, limit: int = 6) -> list[Movie]:
    statement = (
        select(Movie)
        .join(MovieAnalytics)
        .options(_latest_analytics_option())
        .where(Movie.release_date >= today, MovieAnalytics.snapshot_label == "latest")
        .order_by(Movie.release_date.asc(), Movie.title.asc())
        .limit(limit)
    )
    return list(db.scalars(statement).unique().all())


def list_released_movies(db: Session, today: date, limit: int = 12) -> list[Movie]:
    statement = (
        select(Movie)
        .join(MovieAnalytics)
        .options(_latest_analytics_option())
        .where(
            MovieAnalytics.snapshot_label == "latest",
            Movie.release_date < today,
        )
        .order_by(Movie.release_date.desc(), Movie.title.asc())
        .limit(limit)
    )
    return list(db.scalars(statement).unique().all())


def search_movies(db: Session, query: str) -> list[Movie]:
    pattern = f"%{query.lower()}%"
    statement = (
        select(Movie)
        .join(MovieAnalytics)
        .options(_latest_analytics_option())
        .where(
            MovieAnalytics.snapshot_label == "latest",
            or_(
                func.lower(Movie.title).like(pattern),
                func.lower(Movie.overview).like(pattern),
                func.lower(Movie.status).like(pattern),
                func.lower(func.json_extract(Movie.genres, "$")).like(pattern),
            ),
        )
        .order_by(MovieAnalytics.buzz_score.desc(), Movie.title.asc())
    )
    return list(db.scalars(statement).unique().all())


def get_movie_by_id(db: Session, movie_id: int) -> Movie | None:
    statement = (
        select(Movie)
        .options(_latest_analytics_option())
        .where(Movie.id == movie_id)
    )
    return db.scalars(statement).unique().first()


def get_movie_by_slug(db: Session, slug: str) -> Movie | None:
    statement = (
        select(Movie)
        .options(_latest_analytics_option())
        .where(Movie.slug == slug)
    )
    return db.scalars(statement).unique().first()


def get_movie_analytics(db: Session, movie_id: int) -> MovieAnalytics | None:
    statement = (
        select(MovieAnalytics)
        .where(
            MovieAnalytics.movie_id == movie_id,
            MovieAnalytics.snapshot_label == "latest",
        )
    )
    return db.scalar(statement)
