"""
ReelTogether Analytics — FastAPI backend entry point.

Responsibilities:
  - Application lifecycle (startup / shutdown)
  - Middleware stack (CORS, GZip, rate-limit, trusted-host, request context)
  - Router registration
  - Optional database-backed maintenance worker
  - Health / readiness endpoints
"""
from __future__ import annotations

import logging
import logging.config
import threading
import time

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.movie import Movie
from app.models.account import Account, LoginSession
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import movie_nights, accounts, admin, ai, analytics, assistant, movies, ratings, recommendations, search
from app.core.middleware import InMemoryRateLimitMiddleware, RequestContextMiddleware
from app.core.config import settings
from app.services.schema_health import assert_schema_ready
from app.services.bootstrap import initialize_database
from app.services.redis_store import redis_health
from app.services.startup_jobs import (
    get_startup_sync_status,
    run_startup_sync_once,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "root": {"handlers": ["console"], "level": settings.LOG_LEVEL},
        "loggers": {
            "uvicorn": {"propagate": True},
            "uvicorn.access": {"propagate": True},
            "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
        },
    }
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "ReelTogether Analytics API — real-time movie popularity, hype scoring, "
        "trailer analytics, and box-office forecasting powered by TMDB, YouTube, "
        "OMDB, and Wikipedia."
    ),
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

# ---------------------------------------------------------------------------
# Middleware  (order matters — applied bottom-up)
# ---------------------------------------------------------------------------
app.add_middleware(RequestContextMiddleware)

if settings.ENABLE_RATE_LIMIT:
    app.add_middleware(InMemoryRateLimitMiddleware)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id", "X-Response-Time"],
)

if settings.ENABLE_GZIP:
    app.add_middleware(GZipMiddleware, minimum_size=512)


@app.middleware("http")
async def add_response_timing(request: Request, call_next):
    """Attach X-Response-Time header to every response for observability."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(movies.router,   prefix=f"{settings.API_V1_PREFIX}/movies",    tags=["movies"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_PREFIX}/analytics", tags=["analytics"])
app.include_router(search.router,   prefix=f"{settings.API_V1_PREFIX}/search",    tags=["search"])
app.include_router(ai.router,       prefix=f"{settings.API_V1_PREFIX}/ai",        tags=["ai"])
if settings.ENABLE_USER_FEATURES and not settings.is_production:
    app.include_router(ratings.router, prefix=f"{settings.API_V1_PREFIX}/ratings", tags=["ratings"])
    app.include_router(recommendations.router, prefix=f"{settings.API_V1_PREFIX}/recommendations", tags=["recommendations"])
app.include_router(movie_nights.router, prefix=f"{settings.API_V1_PREFIX}/movie-nights", tags=["movie-nights"])
app.include_router(accounts.router, prefix=settings.API_V1_PREFIX, tags=["accounts"])
app.include_router(assistant.router, prefix=f"{settings.API_V1_PREFIX}/assistant", tags=["assistant"])
app.include_router(admin.router,    prefix=f"{settings.API_V1_PREFIX}/admin",     tags=["admin"])


# ---------------------------------------------------------------------------
# Background scheduler — periodic data refresh
# ---------------------------------------------------------------------------
_worker_thread: threading.Thread | None = None
_worker_stop = threading.Event()


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    global _worker_thread

    if settings.is_production:
        from production_check import configuration_checks
        failed = [name for name, passed in configuration_checks().items() if not passed]
        if failed:
            raise RuntimeError("Production configuration checks failed: " + ", ".join(failed))

    # 1. Ensure DB tables exist
    initialize_database()
    logger.info("%s v%s — startup complete", settings.APP_NAME, settings.APP_VERSION)

    # 2. Initial data sync (TMDB + YouTube + AI foundation)
    if settings.ENABLE_STARTUP_SYNC:
        if settings.STARTUP_SYNC_ASYNC:
            from app.services.background_jobs import job_registry
            scheduled = job_registry.schedule_due("startup-sync")
            latest = scheduled or job_registry.latest("startup-sync")
            job_id = latest.id
            logger.info("Startup sync queued asynchronously (job_id=%s)", job_id)
        else:
            logger.info("Running startup sync inline (blocking)")
            run_startup_sync_once()
            logger.info("Startup sync finished")

    if settings.ENABLE_JOB_WORKER:
        from job_worker import run_worker
        _worker_stop.clear()
        _worker_thread = threading.Thread(target=run_worker, args=(_worker_stop,), daemon=True, name="maintenance-worker")
        _worker_thread.start()


@app.on_event("shutdown")
def shutdown_event():
    _worker_stop.set()
    if _worker_thread is not None:
        _worker_thread.join(timeout=5)
    logger.info("%s shutdown complete", settings.APP_NAME)


# ---------------------------------------------------------------------------
# Core routes
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs" if settings.docs_enabled else None,
        "health": "/health",
    }


@app.get("/health", tags=["system"])
def health_check():
    """Full health check including integration status."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "integrations": {
            "tmdb_api": {"configured": settings.tmdb_api_configured},
            "youtube_api": {"configured": settings.youtube_api_configured},
            "omdb_api": {"configured": settings.omdb_api_configured},
            "redis": redis_health(),
        },
        "startup_sync": get_startup_sync_status(),
    }


@app.get("/health/live", tags=["system"])
def liveness_check():
    """Kubernetes liveness probe — always returns 200 if the process is up."""
    return {"status": "live"}


@app.get("/health/ready", tags=["system"])
def readiness_check():
    """Readiness requires the schema for every enabled persisted feature."""
    startup_status = get_startup_sync_status()
    job = startup_status.get("job")
    try:
        with SessionLocal() as db:
            assert_schema_ready(db)
        ready = True
    except Exception:
        ready = False
    status_code = 200 if ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if ready else "warming",
            "ready": ready,
            "startup_sync": startup_status,
        },
    )
