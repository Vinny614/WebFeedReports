"""API request/response DTOs and report models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from .contracts import JobStatus, JobType

SourceHealthStatus = Literal["never", "healthy", "degraded", "failed"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SearchFilters(BaseModel):
    """Retrieval filters applied to the search index (company, topic, dates)."""

    source_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    date_from: datetime | None = None
    date_to: datetime | None = None


class SourceHealth(BaseModel):
    """Current operational health for one configured ingestion source."""

    source_id: str
    status: SourceHealthStatus = "never"
    last_attempt_at: datetime | None = None
    last_success_at: datetime | None = None
    newest_published_at: datetime | None = None
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    document_count: int = 0
    indexed_document_count: int = 0
    chunk_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    latest_error: str | None = None


class SourceHealthSummary(BaseModel):
    total: int = 0
    healthy: int = 0
    degraded: int = 0
    failed: int = 0
    never: int = 0


class QueryRequest(BaseModel):
    query: str
    top: int = 10
    source_ids: list[str] = Field(default_factory=list)
    date_from: datetime | None = None
    date_to: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class QueryResultItem(BaseModel):
    chunk_id: str
    document_id: str
    source_id: str
    score: float
    title: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    snippet: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"] = "user"
    content: str


class ChatRequest(BaseModel):
    """Multi-turn conversation plus retrieval filters for grounded chat."""

    messages: list[ChatMessage] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    date_from: datetime | None = None
    date_to: datetime | None = None


class QueryResponse(BaseModel):
    query: str
    items: list[QueryResultItem]


class ReportTemplateSection(BaseModel):
    """A single heading in a template or a user-defined custom heading."""

    heading: str
    style: Literal["narrative", "items"] = "items"
    guidance: str | None = None
    query: str | None = None
    tags: list[str] = Field(default_factory=list)


class ReportTemplate(BaseModel):
    id: str
    name: str
    description: str | None = None
    default_query: str | None = None
    sections: list[ReportTemplateSection] = Field(default_factory=list)


class RecentHeadingSet(BaseModel):
    """An entry in the most-recently-used custom heading store (last 5)."""

    name: str | None = None
    sections: list[ReportTemplateSection] = Field(default_factory=list)
    used_at: datetime = Field(default_factory=_utcnow)


class ReportRequest(BaseModel):
    query: str
    title: str | None = None
    tags: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    date_from: datetime | None = None
    date_to: datetime | None = None
    template_id: str | None = None
    # When provided, these headings drive section-by-section generation and are
    # recorded in the recent-headings store.
    sections: list[ReportTemplateSection] | None = None


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


class ReportItem(BaseModel):
    """A single news item within an item-style section (BAE-style)."""

    title: str
    url: str | None = None
    source: str | None = None
    published_at: datetime | None = None
    summary: str = ""


class ReportSection(BaseModel):
    heading: str
    style: Literal["narrative", "items"] = "narrative"
    content: str = ""
    items: list["ReportItem"] = Field(default_factory=list)


class ReportCitation(BaseModel):
    source_id: str
    title: str | None = None
    url: str | None = None
