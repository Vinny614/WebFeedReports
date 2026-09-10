"""Core domain models shared across all services."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SourceType(str, Enum):
    RSS = "rss"
    WEB = "web"


class CrawlOptions(BaseModel):
    depth: int = 0
    max_pages: int | None = None


class Source(BaseModel):
    """A configured ingestion source (RSS feed or web page)."""

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    type: SourceType
    url: HttpUrl
    enabled: bool = True
    schedule: str | None = None
    tags: list[str] = Field(default_factory=list)
    crawl: CrawlOptions | None = None
    # RSS content handling: feed trusts the supplied body, article always
    # fetches the linked page, and auto fetches when only a summary is present.
    content_mode: Literal["feed", "auto", "article"] = "auto"
    expected_host: str | None = None
    expected_text: str | None = None
    min_documents: int = 1
    min_text_chars: int = 100
    max_age_days: int | None = 45


class Document(BaseModel):
    """A single ingested item before chunking/indexing."""

    id: str
    source_id: str
    url: HttpUrl
    title: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=_utcnow)
    raw_blob_path: str | None = None
    # Raw content supplied directly by the source (e.g. an RSS entry's
    # content:encoded/summary). Preferred over re-fetching the landing page.
    content_html: str | None = None
    content_is_summary: bool = False


class Chunk(BaseModel):
    """A retrievable, embedded fragment of a Document."""

    id: str
    document_id: str
    source_id: str
    ordinal: int
    text: str
    url: HttpUrl | None = None
    title: str | None = None
    published_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None
