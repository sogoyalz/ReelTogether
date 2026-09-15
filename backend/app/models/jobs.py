from datetime import datetime
from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(40), index=True)
    active_name: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(16))
    queued_at: Mapped[datetime] = mapped_column(DateTime)
    available_at: Mapped[datetime] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String(100), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class QueueControl(Base):
    __tablename__ = "job_queue_control"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=0)


class JobSchedule(Base):
    __tablename__ = "job_schedules"
    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    next_run: Mapped[datetime] = mapped_column(DateTime)
