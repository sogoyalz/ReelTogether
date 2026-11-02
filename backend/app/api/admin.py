from __future__ import annotations

import hmac
from app.schemas.jobs import JobAcknowledgement, JobResponse, JobList

from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.services.background_jobs import job_registry, serialize_job, QueueFull
from app.services.startup_jobs import (
    enqueue_ai_refresh,
    enqueue_startup_sync,
    enqueue_tmdb_sync,
    enqueue_youtube_refresh,
)

router = APIRouter()


@router.get('/metrics/prometheus')
def prometheus_metrics(x_admin_key: str | None = Header(default=None)):
    _authorize_admin(x_admin_key)
    from fastapi.responses import Response
    from sqlalchemy import select, func
    from app.db.session import SessionLocal
    from app.models.jobs import BackgroundJob
    from app.services.background_jobs import utcnow
    from app.services.operational_metrics import prometheus
    with SessionLocal() as db:
        oldest = db.scalar(select(func.min(BackgroundJob.queued_at)).where(BackgroundJob.status == 'queued'))
        expired = db.scalar(select(func.count()).select_from(BackgroundJob).where(BackgroundJob.status == 'running', BackgroundJob.lease_until <= utcnow()))
        from app.models.account import AccountErasure
        pending_erasure = db.scalar(select(func.count()).select_from(AccountErasure).where(AccountErasure.exported_at.is_(None)))
    age = max(0, (utcnow()-oldest).total_seconds()) if oldest else 0
    body = prometheus() + f'# TYPE reeltogether_queue_oldest_seconds gauge\nreeltogether_queue_oldest_seconds {age}\n# TYPE reeltogether_expired_leases gauge\nreeltogether_expired_leases {expired}\n'
    body += f'# TYPE reeltogether_pending_erasure_receipts gauge\nreeltogether_pending_erasure_receipts {pending_erasure}\n'
    return Response(body, media_type='text/plain; version=0.0.4', headers={'Cache-Control':'private, no-store'})


def enqueue_response(enqueue):
    try:
        job_id = enqueue()
    except QueueFull:
        raise HTTPException(503, "Maintenance queue is full; retry later", headers={"Retry-After": "60"}) from None
    job = job_registry.get(job_id)
    return {"job_id": job_id, "status": job.status}



def _authorize_admin(x_admin_key: str | None = Header(default=None)) -> None:
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Set ADMIN_API_KEY to enable maintenance endpoints")
    if not hmac.compare_digest((x_admin_key or "").encode(), settings.ADMIN_API_KEY.encode()):
        raise HTTPException(status_code=401, detail="Invalid admin key")


@router.get("/jobs", response_model=JobList)
def list_jobs(x_admin_key: str | None = Header(default=None)):
    _authorize_admin(x_admin_key)
    return {"jobs": [serialize_job(job) for job in job_registry.list()]}


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, x_admin_key: str | None = Header(default=None)):
    _authorize_admin(x_admin_key)
    job = job_registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return serialize_job(job)


@router.post("/jobs/startup-sync", response_model=JobAcknowledgement)
def run_startup_sync(x_admin_key: str | None = Header(default=None)):
    _authorize_admin(x_admin_key)
    return enqueue_response(enqueue_startup_sync)


@router.post("/jobs/tmdb-sync", response_model=JobAcknowledgement)
def run_tmdb_sync(x_admin_key: str | None = Header(default=None)):
    _authorize_admin(x_admin_key)
    return enqueue_response(enqueue_tmdb_sync)


@router.post("/jobs/youtube-refresh", response_model=JobAcknowledgement)
def run_youtube_refresh(x_admin_key: str | None = Header(default=None)):
    _authorize_admin(x_admin_key)
    return enqueue_response(enqueue_youtube_refresh)


@router.post("/jobs/ai-refresh", response_model=JobAcknowledgement)
def run_ai_refresh(x_admin_key: str | None = Header(default=None)):
    _authorize_admin(x_admin_key)
    return enqueue_response(enqueue_ai_refresh)


@router.get("/metrics")
def operational_metrics(x_admin_key: str | None = Header(default=None)):
    _authorize_admin(x_admin_key)
    from app.services.operational_metrics import snapshot
    return snapshot()
