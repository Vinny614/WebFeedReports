"""Job and message contracts exchanged between API and worker via Service Bus."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobType(str, Enum):
    INGEST = "ingest"
    REPORT = "report"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IngestJob(BaseModel):
    """Message body for an ingestion job placed on the ingest queue."""

    type: JobType = JobType.INGEST
    job_id: str
    source_ids: list[str] = Field(default_factory=list)  # empty = all enabled
    requested_at: datetime = Field(default_factory=_utcnow)


class ReportJob(BaseModel):
    """Message body for a report-generation job placed on the report queue."""

    type: JobType = JobType.REPORT
    job_id: str
    query: str
    title: str | None = None
    filters: dict[str, str] = Field(default_factory=dict)
    requested_at: datetime = Field(default_factory=_utcnow)


class JobRecord(BaseModel):
    """Persisted job state (Table Storage) surfaced through the API."""

    job_id: str
    type: JobType
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    error: str | None = None
    result_ref: str | None = None  # e.g. blob path or report id
