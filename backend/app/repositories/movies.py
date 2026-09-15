from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select, cast, String
from sqlalchemy.orm import Session, selectinload

from app.models.ai import ReviewSentiment
from app.models.movie import Movie, MovieAnalytics


def _latest_analytics_option():
    return selectinload(Movie.analytics_snapshots)


def list_movies(db: Session) -> list[Movie]:
    statement = select(Movie).options(_latest_analytics_option()).order_by(Movie.title.asc())
    return list(db.scalars(statement).unique().all())


def summary_analytics_option():
    return selectinload(Movie.latest_snapshots)


def latest_analytics(movie: Movie) -> MovieAnalytics | None:
    # Honor an already-loaded writable collection (including pending updates).
    if "analytics_snapshots" in movie.__dict__:
        return next((row for row in movie.analytics_snapshots if row.snapshot_label == "latest"), None)
    return next(iter(movie.latest_snapshots), None)


def list_summary_movies(db: Session, limit: int | None = None) -> list[Movie]:
    statement = select(Movie).options(summary_analytics_option()).order_by(Movie.title.asc(), Movie.id.asc())
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).all())


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
        .where(Movie.release_date > today, MovieAnalytics.snapshot_label == "latest")
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
            Movie.release_date <= today,
        )
        .order_by(Movie.release_date.desc(), Movie.title.asc())
        .limit(limit)
    )
    return list(db.scalars(statement).unique().all())


def search_movies(db: Session, query: str, limit: int | None = None) -> list[Movie]:
    pattern = f"%{query.lower()}%"
    statement = (
        select(Movie)
        .outerjoin(MovieAnalytics, (MovieAnalytics.movie_id == Movie.id) & (MovieAnalytics.snapshot_label == "latest"))
        .options(_latest_analytics_option())
        .where(
            or_(
                func.lower(Movie.title).like(pattern),
                func.lower(Movie.overview).like(pattern),
                func.lower(Movie.status).like(pattern),
                func.lower(cast(Movie.genres, String)).like(pattern),
            ),
        )
        .order_by(MovieAnalytics.buzz_score.desc(), Movie.title.asc())
    )
    if limit is not None:
        statement = statement.limit(limit)
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


def upsert_review_sentiments(db: Session, movie_id: int, reviews: list[dict]) -> int:
    existing = {
        (item.author, item.created_at.isoformat(), item.source): item
        for item in db.scalars(
            select(ReviewSentiment).where(ReviewSentiment.movie_id == movie_id)
        ).all()
    }

    created = 0
    for review in reviews:
        key = (review["author"], review["created_at"].isoformat(), review["source"])
        if key in existing and existing[key].analyzed_at is not None:
            continue

        if key in existing:
            row = existing[key]
            row.content_snippet = review["content"][:200]
            row.sentiment_score = review["sentiment_score"]
            row.sentiment_label = review["sentiment_label"]
            row.confidence = review["confidence"]
            row.source = review["source"]
        else:
            db.add(
                ReviewSentiment(
                    movie_id=movie_id,
                    author=review["author"],
                    content_snippet=review["content"][:200],
                    created_at=review["created_at"],
                    sentiment_score=review["sentiment_score"],
                    sentiment_label=review["sentiment_label"],
                    confidence=review["confidence"],
                    source=review["source"],
                )
            )
            created += 1

    db.commit()
    return created


def list_review_sentiments(db: Session, movie_id: int) -> list[ReviewSentiment]:
    statement = (
        select(ReviewSentiment)
        .where(ReviewSentiment.movie_id == movie_id)
        .order_by(ReviewSentiment.created_at.asc(), ReviewSentiment.id.asc())
    )
    return list(db.scalars(statement).all())
