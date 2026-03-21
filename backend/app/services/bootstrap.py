from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as _models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models.movie import Movie
from app.services.mock_data import build_models


def initialize_database() -> None:
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)


def seed_database_if_empty(db: Session) -> None:
    if settings.tmdb_api_configured:
        return

    existing_movie = db.scalar(select(Movie.id).limit(1))
    if existing_movie is not None:
        _seed_missing_movies(db)
        return

    for movie, analytics in build_models():
        movie.analytics_snapshots.append(analytics)
        db.add(movie)

    db.commit()


def _seed_missing_movies(db: Session) -> None:
    existing_slugs = set(db.scalars(select(Movie.slug)).all())
    added = False

    for movie, analytics in build_models():
        if movie.slug in existing_slugs:
            continue
        movie.analytics_snapshots.append(analytics)
        db.add(movie)
        added = True

    if added:
        db.commit()
