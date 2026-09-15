from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class JobRecord:
    id: str
    name: str
    status: str = "queued"
    queued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    result: dict[str, Any] | None = None


class JobRegistry:
    def __init__(self, max_jobs: int = 100) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._order: deque[str] = deque()
        self._max_jobs = max_jobs
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="movie-job")

    def enqueue(self, name: str, fn: Callable[..., dict[str, Any] | None], *args, **kwargs) -> JobRecord:
        with self._lock:
            for existing in self._jobs.values():
                if existing.name == name and existing.status in {"queued", "running"}:
                    return existing
            active = sum(job.status in {"queued", "running"} for job in self._jobs.values())
            if active >= self._max_jobs:
                raise RuntimeError("Background queue is full")
            while len(self._order) >= self._max_jobs:
                finished = next((key for key in self._order if self._jobs[key].status not in {"queued", "running"}), None)
                if finished is None:
                    break
                self._order.remove(finished)
                del self._jobs[finished]
            job = JobRecord(id=str(uuid.uuid4()), name=name)
            self._jobs[job.id] = job
            self._order.append(job.id)
        self._executor.submit(self._run_job, job.id, fn, args, kwargs)
        return job

    def _run_job(
        self,
        job_id: str,
        fn: Callable[..., dict[str, Any] | None],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        self.update(job_id, status="running", started_at=datetime.now(timezone.utc).isoformat())
        started = time.monotonic()
        try:
            result = fn(*args, **kwargs) or {}
            elapsed_ms = int((time.monotonic() - started) * 1000)
            result.setdefault("elapsed_ms", elapsed_ms)
            self.update(
                job_id,
                status="completed",
                finished_at=datetime.now(timezone.utc).isoformat(),
                result=result,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Background job failed: %s", job_id)
            self.update(
                job_id,
                status="failed",
                finished_at=datetime.now(timezone.utc).isoformat(),
                error=str(exc),
            )

    def update(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in fields.items():
                setattr(job, key, value)

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[JobRecord]:
        with self._lock:
            return [self._jobs[job_id] for job_id in reversed(self._order)]


job_registry = JobRegistry()


def serialize_job(job: JobRecord) -> dict[str, Any]:
    return asdict(job)
