"""API request/response DTOs and report models."""

from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, Field

from .contracts import JobStatus, JobType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class QueryRequest(BaseModel):
    query: str
    top: int = 10
    tags: list[str] = Field(default_factory=list)


class QueryResultItem(BaseModel):
    chunk_id: str
    document_id: str
    source_id: str
    score: float
    title: str | None = None
    url: str | None = None
    snippet: str


class QueryResponse(BaseModel):
    query: str
    items: list[QueryResultItem]


class ReportRequest(BaseModel):
    query: str
    title: str | None = None
    tags: list[str] = Field(default_factory=list)


class JobSubmittedResponse(BaseModel):
    job_id: str
    type: JobType
    status: JobStatus


class JobStatusResponse(BaseModel):
    job_id: str
    type: JobType
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    error: str | None = None
    result_ref: str | None = None


class BriefingReport(BaseModel):
    report_id: str
    title: str
    query: str
    generated_at: datetime = Field(default_factory=_utcnow)
    summary: str
    sections: list["ReportSection"] = Field(default_factory=list)
    citations: list["ReportCitation"] = Field(default_factory=list)


class ReportSection(BaseModel):
    heading: str
    content: str


class ReportCitation(BaseModel):
    source_id: str
    title: str | None = None
    url: str | None = None
