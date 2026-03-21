import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import admin, ai, analytics, movies, search
from app.core.middleware import InMemoryRateLimitMiddleware, RequestContextMiddleware
from app.core.config import settings
from app.services.bootstrap import initialize_database
from app.services.startup_jobs import enqueue_startup_sync, get_startup_sync_status, run_startup_sync_once

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(InMemoryRateLimitMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if settings.ENABLE_GZIP:
    app.add_middleware(GZipMiddleware, minimum_size=1024)

app.include_router(movies.router, prefix=f"{settings.API_V1_PREFIX}/movies", tags=["movies"])
app.include_router(
    analytics.router,
    prefix=f"{settings.API_V1_PREFIX}/analytics",
    tags=["analytics"],
)
app.include_router(search.router, prefix=f"{settings.API_V1_PREFIX}/search", tags=["search"])
app.include_router(ai.router, prefix=f"{settings.API_V1_PREFIX}/ai", tags=["ai"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["admin"])


@app.on_event("startup")
def startup_event():
    initialize_database()
    if settings.ENABLE_STARTUP_SYNC:
        if settings.STARTUP_SYNC_ASYNC:
            job_id = enqueue_startup_sync()
            logger.info("Startup sync queued in background: job_id=%s", job_id)
        else:
            logger.info("Startup sync running inline before serving traffic.")
            run_startup_sync_once()


@app.get("/")
def root():
    return {
        "message": f"{settings.APP_NAME} v{settings.APP_VERSION}",
        "docs": "/docs" if settings.docs_enabled else None,
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
        "startup_sync": get_startup_sync_status(),
    }


@app.get("/health/live")
def liveness_check():
    return {"status": "live"}


@app.get("/health/ready")
def readiness_check():
    startup_status = get_startup_sync_status()
    job = startup_status.get("job")
    ready = not settings.ENABLE_STARTUP_SYNC or job is None or job["status"] == "completed"
    return {
        "status": "ready" if ready else "warming",
        "ready": ready,
        "startup_sync": startup_status,
    }
