"""Fence worker database commits against lease loss in the same transaction.

The queue control row serializes claim and commit decisions. A stale handler
may finish an HTTP read, but its transactional writes must roll back.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from sqlalchemy import event, select, update
from sqlalchemy.orm import Session
from app.models.jobs import BackgroundJob, QueueControl
from datetime import datetime, timezone
from app.core.config import settings

_lease = ContextVar('catalog_job_lease', default=None)


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LeaseLost(RuntimeError):
    pass


@event.listens_for(Session, 'before_flush')
def require_worker_for_catalog(db, *_):
    if settings.is_production and _lease.get() is None and any(
        type(obj).__module__ in {'app.models.movie','app.models.ai'}
        for obj in db.new | db.dirty | db.deleted):
        raise LeaseLost('Production catalog writes require the maintenance worker')


@contextmanager
def fenced_job(job, lost):
    token = _lease.set((job.id, job.lease_token, lost))
    try:
        yield
    finally:
        _lease.reset(token)


@event.listens_for(Session, 'before_commit')
def verify_commit_lease(db):
    lease = _lease.get()
    if lease is None:
        return
    job_id, token, lost = lease
    if lost.is_set():
        raise LeaseLost('Maintenance lease lost')
    # Do not use a second session: the check and catalog writes must commit
    # together while claims are blocked on this exact queue-control row.
    db.execute(update(QueueControl).where(QueueControl.id == 1).values(version=QueueControl.version + 1))
    owned = db.scalar(select(BackgroundJob.id).where(
        BackgroundJob.id == job_id, BackgroundJob.lease_token == token,
        BackgroundJob.status == 'running', BackgroundJob.lease_until > utcnow()))
    if owned is None:
        raise LeaseLost('Maintenance lease lost')
