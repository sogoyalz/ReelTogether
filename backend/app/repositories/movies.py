from __future__ import annotations

from app.services.review_identity import review_key

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
        .options(summary_analytics_option())
        .where(MovieAnalytics.snapshot_label == "latest")
        .order_by(MovieAnalytics.buzz_score.desc(), Movie.title.asc())
        .limit(limit)
    )
    return list(db.scalars(statement).unique().all())


def list_upcoming_movies(db: Session, today: date, limit: int = 6) -> list[Movie]:
    statement = (
        select(Movie)
        .join(MovieAnalytics)
        .options(summary_analytics_option())
        .where(Movie.release_date > today, MovieAnalytics.snapshot_label == "latest")
        .order_by(Movie.release_date.asc(), Movie.title.asc())
        .limit(limit)
    )
    return list(db.scalars(statement).unique().all())


def list_released_movies(db: Session, today: date, limit: int = 12) -> list[Movie]:
    statement = (
        select(Movie)
        .join(MovieAnalytics)
        .options(summary_analytics_option())
        .where(
            MovieAnalytics.snapshot_label == "latest",
            Movie.release_date <= today,
        )
        .order_by(Movie.release_date.desc(), Movie.title.asc())
        .limit(limit)
    )
    return list(db.scalars(statement).unique().all())


def search_movies(db: Session, query: str, limit: int | None = None) -> list[Movie]:
    from app.services.catalog_sql import text_lower
    lower = text_lower(db)
    pattern = query.lower()
    statement = (
        select(Movie)
        .outerjoin(MovieAnalytics, (MovieAnalytics.movie_id == Movie.id) & (MovieAnalytics.snapshot_label == "latest"))
        .options(summary_analytics_option())
        .where(
            or_(
                lower(Movie.title).contains(pattern, autoescape=True),
                lower(Movie.overview).contains(pattern, autoescape=True),
                lower(Movie.status).contains(pattern, autoescape=True),
                lower(cast(Movie.genres, String)).contains(pattern, autoescape=True),
            ),
        )
        .order_by(MovieAnalytics.buzz_score.desc(), Movie.title.asc())
    )
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).unique().all())


def get_movie_by_id(db: Session, movie_id: int, *, with_history: bool = True) -> Movie | None:
    statement = (
        select(Movie)
        .options(_latest_analytics_option() if with_history else summary_analytics_option())
        .where(Movie.id == movie_id)
    )
    return db.scalars(statement).unique().first()


def get_movie_by_slug(db: Session, slug: str, *, with_history: bool = True) -> Movie | None:
    statement = (
        select(Movie)
        .options(_latest_analytics_option() if with_history else summary_analytics_option())
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
        review_key(item.author, item.created_at, item.source, item.source_review_id): item
        for item in db.scalars(
            select(ReviewSentiment).where(ReviewSentiment.movie_id == movie_id)
        ).all()
    }

    created = 0
    for review in reviews:
        key = review_key(review["author"], review["created_at"], review["source"], review.get("source_review_id"))
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
            row = ReviewSentiment(
                    movie_id=movie_id,
                    source_review_id=review.get("source_review_id"),
                    author=review["author"],
                    content_snippet=review["content"][:200],
                    created_at=review["created_at"],
                    sentiment_score=review["sentiment_score"],
                    sentiment_label=review["sentiment_label"],
                    confidence=review["confidence"],
                    source=review["source"],
                )
            db.add(row)
            existing[key] = row
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


def catalog_dashboard_stats(db: Session):
    count, hype, buzz = db.execute(select(func.count(MovieAnalytics.id), func.avg(MovieAnalytics.hype_score),
        func.avg(MovieAnalytics.buzz_score)).join(Movie, Movie.id == MovieAnalytics.movie_id).where(
            MovieAnalytics.snapshot_label == "latest")).one()
    return {"tracked_movies":count, "average_hype_score":round(hype or 0.0,2), "average_buzz_score":round(buzz or 0.0,2)}


def list_most_hyped_movies(db: Session, limit=5):
    return list(db.scalars(select(Movie).join(MovieAnalytics).where(MovieAnalytics.snapshot_label == "latest")
        .order_by(MovieAnalytics.hype_score.desc(), Movie.id.asc()).limit(limit).options(summary_analytics_option())))
