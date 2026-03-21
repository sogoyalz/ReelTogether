import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, movies, search
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.bootstrap import initialize_database, seed_database_if_empty
from app.services.tmdb import sync_tmdb_catalog
from app.services.youtube_analytics import refresh_all_movie_analytics

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(movies.router, prefix=f"{settings.API_V1_PREFIX}/movies", tags=["movies"])
app.include_router(
    analytics.router,
    prefix=f"{settings.API_V1_PREFIX}/analytics",
    tags=["analytics"],
)
app.include_router(search.router, prefix=f"{settings.API_V1_PREFIX}/search", tags=["search"])


@app.on_event("startup")
def startup_event():
    if settings.tmdb_api_configured:
        logger.info("TMDB_API_KEY is configured. Syncing live catalog from TMDB.")
    if not settings.youtube_api_configured:
        logger.warning("YOUTUBE_API_KEY is not configured. Backend will continue using seeded analytics data.")

    initialize_database()
    with SessionLocal() as db:
        if settings.tmdb_api_configured:
            tmdb_result = sync_tmdb_catalog(db)
            logger.info(
                "TMDB sync complete: synced=%s created=%s updated=%s failed=%s",
                tmdb_result.synced_movies,
                tmdb_result.created_movies,
                tmdb_result.updated_movies,
                tmdb_result.failed_movies,
            )
        seed_database_if_empty(db)
        if settings.youtube_api_configured:
            result = refresh_all_movie_analytics(db)
            logger.info(
                "YouTube analytics refresh complete: refreshed=%s skipped=%s failed=%s",
                result.refreshed_movies,
                result.skipped_movies,
                result.failed_movies,
            )


@app.get("/")
def root():
    return {
        "message": f"{settings.APP_NAME} v{settings.APP_VERSION}",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "integrations": {
            "tmdb_api_configured": settings.tmdb_api_configured,
            "youtube_api_configured": settings.youtube_api_configured,
            "omdb_api_configured": settings.omdb_api_configured,
        },
    }
