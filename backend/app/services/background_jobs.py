"""Database-backed, at-least-once maintenance queue with fenced leases."""
from datetime import datetime, timedelta, timezone
import uuid
from sqlalchemy import select, update, func, or_
from sqlalchemy.exc import IntegrityError
from app.db.session import SessionLocal
from app.models.jobs import BackgroundJob, QueueControl, JobSchedule

JOB_NAMES = {"startup-sync", "tmdb-sync", "youtube-refresh", "ai-refresh"}
MAX_ATTEMPTS = 3


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def serialize_job(job):
    fields = ("id", "name", "status", "queued_at", "started_at", "finished_at", "attempts", "available_at", "error", "result")
    return {field: (value.isoformat()+"Z" if isinstance(value := getattr(job, field), datetime) else value) for field in fields}


class QueueFull(RuntimeError):
    pass


class JobRegistry:
    def __init__(self, max_jobs=100, session_factory=None):
        self.max_jobs = max_jobs
        self.session_factory = session_factory or SessionLocal

    def _lock(self, db):
        # Migrations seed this row. Lazy insertion also supports create_all fixtures.
        if db.get(QueueControl, 1) is None:
            try:
                with db.begin_nested():
                    db.add(QueueControl(id=1, version=0)); db.flush()
            except IntegrityError:
                pass
        db.execute(update(QueueControl).where(QueueControl.id == 1).values(version=QueueControl.version+1))

    def _enqueue(self, db, name):
        existing = db.scalar(select(BackgroundJob).where(BackgroundJob.active_name == name))
        if existing:
            return existing
        count = db.scalar(select(func.count()).select_from(BackgroundJob).where(BackgroundJob.active_name.is_not(None)))
        if count >= self.max_jobs:
            raise QueueFull("Maintenance queue is full")
        finished = list(db.scalars(select(BackgroundJob).where(BackgroundJob.active_name.is_(None)).order_by(BackgroundJob.queued_at.desc())))
        for old in finished[max(0, self.max_jobs-count-1):]:
            db.delete(old)
        now = utcnow()
        job = BackgroundJob(id=str(uuid.uuid4()), name=name, active_name=name, status="queued", queued_at=now, available_at=now, attempts=0)
        db.add(job); db.flush()
        return job

    def enqueue(self, name):
        if name not in JOB_NAMES:
            raise ValueError("Unknown maintenance operation")
        with self.session_factory() as db:
            self._lock(db)
            job = self._enqueue(db, name)
            db.commit(); db.refresh(job); db.expunge(job)
            return job

    def schedule_due(self, name, interval=21600):
        if name not in JOB_NAMES or interval < 1:
            raise ValueError("Invalid maintenance schedule")
        with self.session_factory() as db:
            self._lock(db)
            now = utcnow()
            schedule = db.get(JobSchedule, name)
            if schedule and schedule.next_run > now:
                return None
            job = self._enqueue(db, name)
            if schedule:
                schedule.next_run = now+timedelta(seconds=interval)
            else:
                db.add(JobSchedule(name=name, next_run=now+timedelta(seconds=interval)))
            db.commit(); db.refresh(job); db.expunge(job)
            return job

    def claim(self, lease_seconds=120):
        with self.session_factory() as db:
            self._lock(db)
            now = utcnow()
            jobs = list(db.scalars(select(BackgroundJob).where(or_(
                (BackgroundJob.status == "queued") & (BackgroundJob.available_at <= now),
                (BackgroundJob.status == "running") & (BackgroundJob.lease_until <= now),
            )).order_by(BackgroundJob.queued_at)))
            for job in jobs:
                if job.attempts >= MAX_ATTEMPTS:
                    job.status="failed"; job.active_name=None; job.finished_at=now; job.error="Worker lease expired"
                    job.lease_token=None; job.lease_until=None
                    continue
                job.status="running"; job.attempts+=1; job.started_at=now; job.error=None
                job.lease_token=str(uuid.uuid4()); job.lease_until=now+timedelta(seconds=lease_seconds)
                db.commit(); db.refresh(job); db.expunge(job)
                return job
            db.commit()
            return None

    def heartbeat(self, job_id, token, lease_seconds=120):
        with self.session_factory() as db:
            now=utcnow()
            changed=db.execute(update(BackgroundJob).where(BackgroundJob.id==job_id, BackgroundJob.lease_token==token,
                BackgroundJob.status=="running", BackgroundJob.lease_until>now).values(lease_until=now+timedelta(seconds=lease_seconds)))
            db.commit()
            return changed.rowcount == 1

    def finish(self, job_id, token, *, result=None, error=None):
        with self.session_factory() as db:
            self._lock(db)
            job=db.get(BackgroundJob,job_id)
            now=utcnow()
            if not job or job.status!="running" or job.lease_token!=token or job.lease_until<=now:
                return False
            if error and job.attempts < MAX_ATTEMPTS:
                job.status="queued"; job.available_at=now+timedelta(seconds=5*2**job.attempts)
            else:
                job.status="failed" if error else "completed"; job.active_name=None; job.finished_at=now
            job.error=error; job.result=result; job.lease_until=None; job.lease_token=None
            db.commit()
            return True

    def get(self, job_id):
        with self.session_factory() as db:
            job=db.get(BackgroundJob,job_id)
            if job: db.expunge(job)
            return job

    def list(self):
        with self.session_factory() as db:
            return list(db.scalars(select(BackgroundJob).order_by(BackgroundJob.queued_at.desc()).limit(self.max_jobs)))

    def latest(self, name):
        with self.session_factory() as db:
            return db.scalar(select(BackgroundJob).where(BackgroundJob.name==name).order_by(BackgroundJob.queued_at.desc()).limit(1))


job_registry = JobRegistry()
