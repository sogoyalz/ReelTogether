from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict

JobStatus = Literal['queued','running','completed','failed']

class JobAcknowledgement(BaseModel):
    model_config = ConfigDict(extra='forbid')
    job_id: str
    status: JobStatus

class JobResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    name: str
    status: JobStatus
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    attempts: int
    available_at: datetime
    error: str | None
    result: dict[str,Any] | None

class JobList(BaseModel):
    model_config = ConfigDict(extra='forbid')
    jobs: list[JobResponse]
