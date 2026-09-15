from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.services.background_jobs import job_registry, serialize_job
from app.services.startup_jobs import (
    enqueue_ai_refresh,
    enqueue_startup_sync,
    enqueue_tmdb_sync,
    enqueue_youtube_refresh,
)

router = APIRouter()


def _authorize_admin(x_admin_key: str | None = Header(default=None)) -> None:
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Set ADMIN_API_KEY to enable maintenance endpoints")
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")


@router.get("/jobs")
def list_jobs(x_admin_key: str | None = Header(default=None)):
    _authorize_admin(x_admin_key)
    return {"jobs": [serialize_job(job) for job in job_registry.list()]}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, x_admin_key: str | None = Header(default=None)):
    _authorize_admin(x_admin_key)
    job = job_registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return serialize_job(job)


@router.post("/jobs/startup-sync")
def run_startup_sync(x_admin_key: str | None = Header(default=None)):
    _authorize_admin(x_admin_key)
    job_id = enqueue_startup_sync()
    return {"job_id": job_id, "status": "queued"}


@router.post("/jobs/tmdb-sync")
def run_tmdb_sync(x_admin_key: str | None = Header(default=None)):
    _authorize_admin(x_admin_key)
    job_id = enqueue_tmdb_sync()
    return {"job_id": job_id, "status": "queued"}


@router.post("/jobs/youtube-refresh")
def run_youtube_refresh(x_admin_key: str | None = Header(default=None)):
    _authorize_admin(x_admin_key)
    job_id = enqueue_youtube_refresh()
    return {"job_id": job_id, "status": "queued"}


@router.post("/jobs/ai-refresh")
def run_ai_refresh(x_admin_key: str | None = Header(default=None)):
    _authorize_admin(x_admin_key)
    job_id = enqueue_ai_refresh()
    return {"job_id": job_id, "status": "queued"}
