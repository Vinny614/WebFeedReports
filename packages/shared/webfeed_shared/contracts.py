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
    reset: bool = False  # when true, purge + recreate the index before ingest
    requested_at: datetime = Field(default_factory=_utcnow)


class ReportJob(BaseModel):
    """Message body for a report-generation job placed on the report queue."""

    type: JobType = JobType.REPORT
    job_id: str
    query: str
    title: str | None = None
    filters: dict[str, str] = Field(default_factory=dict)
    # Optional template-driven generation. template_id selects a seeded template;
    # sections carries the (possibly user-edited) headings as plain dicts to avoid
    # a circular import with api_models. The worker rebuilds them via
    # ReportTemplateSection.model_validate.
    template_id: str | None = None
    sections: list[dict] | None = None
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
