from __future__ import annotations

import logging

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.movie import Movie
from app.services.ai_foundation import ensure_ai_foundation
from app.services.background_jobs import job_registry, serialize_job
from sqlalchemy.exc import SQLAlchemyError
from app.services.bootstrap import seed_database_if_empty
from app.services.catalog_browser import clear_browse_cache
from app.services.rag_service import initialize_rag_catalog, refresh_embeddings
from app.services.review_fetcher import refresh_review_sentiments_for_movie
from app.services.tmdb import sync_tmdb_catalog
from app.services.youtube_analytics import refresh_all_movie_analytics

logger = logging.getLogger(__name__)

def enqueue_startup_sync() -> str:
    return job_registry.enqueue("startup-sync").id


def run_startup_sync_once() -> dict:
    return _run_startup_sync()


def get_startup_sync_status() -> dict:
    try:
        job = job_registry.latest("startup-sync")
    except SQLAlchemyError:
        job = None
    return {"enabled": settings.ENABLE_STARTUP_SYNC, "async": settings.STARTUP_SYNC_ASYNC,
            "job": serialize_job(job) if job else None}


def enqueue_tmdb_sync() -> str:
    return job_registry.enqueue("tmdb-sync").id


def enqueue_youtube_refresh() -> str:
    return job_registry.enqueue("youtube-refresh").id


def enqueue_ai_refresh() -> str:
    return job_registry.enqueue("ai-refresh").id


def _run_startup_sync() -> dict:
    result = {
        "seeded_catalog": False,
        "tmdb": None,
        "youtube": None,
        "ai_foundation": False,
        "rag": None,
    }
    with SessionLocal() as db:
        if settings.tmdb_api_configured:
            tmdb_result = sync_tmdb_catalog(db)
            clear_browse_cache()
            result["tmdb"] = {
                "synced_movies": tmdb_result.synced_movies,
                "created_movies": tmdb_result.created_movies,
                "updated_movies": tmdb_result.updated_movies,
                "failed_movies": tmdb_result.failed_movies,
            }
            logger.info("Startup TMDB sync complete: %s", result["tmdb"])
        else:
            seed_database_if_empty(db)
            result["seeded_catalog"] = True

        ensure_ai_foundation(db)
        result["ai_foundation"] = True
        if settings.ENABLE_RAG:
            result["rag"] = initialize_rag_catalog(db)

        if settings.youtube_api_configured:
            youtube_result = refresh_all_movie_analytics(db)
            clear_browse_cache()
            result["youtube"] = {
                "refreshed_movies": youtube_result.refreshed_movies,
                "skipped_movies": youtube_result.skipped_movies,
                "failed_movies": youtube_result.failed_movies,
            }
            logger.info("Startup YouTube refresh complete: %s", result["youtube"])

    return result


def _run_tmdb_sync() -> dict:
    with SessionLocal() as db:
        result = sync_tmdb_catalog(db)
        clear_browse_cache()
        ensure_ai_foundation(db)
        return {
            "synced_movies": result.synced_movies,
            "created_movies": result.created_movies,
            "updated_movies": result.updated_movies,
            "failed_movies": result.failed_movies,
        }


def _run_youtube_refresh() -> dict:
    with SessionLocal() as db:
        result = refresh_all_movie_analytics(db)
        clear_browse_cache()
        return {
            "refreshed_movies": result.refreshed_movies,
            "skipped_movies": result.skipped_movies,
            "failed_movies": result.failed_movies,
        }


def _run_ai_refresh() -> dict:
    with SessionLocal() as db:
        ensure_ai_foundation(db)
        movie_ids = [movie.id for movie in db.query(Movie).all()]
        refreshed = refresh_embeddings(db, movie_ids) if settings.ENABLE_RAG else 0
        review_refreshes = 0
        review_failures: list[dict[str, object]] = []
        for movie_id in movie_ids:
            try:
                result = refresh_review_sentiments_for_movie(db, movie_id)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Review sentiment refresh failed for movie %s", movie_id)
                review_failures.append({"movie_id": movie_id, "error": type(exc).__name__})
                db.rollback()
                continue
            review_refreshes += result["new_reviews"]
        return {
            "ai_foundation": True,
            "rag_embeddings_refreshed": refreshed,
            "review_sentiments_refreshed": review_refreshes,
            "review_sentiment_failures": review_failures,
        }
