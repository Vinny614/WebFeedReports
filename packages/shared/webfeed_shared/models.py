"""Core domain models shared across all services."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

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


class Document(BaseModel):
    """A single ingested item before chunking/indexing."""

    id: str
    source_id: str
    url: HttpUrl
    title: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=_utcnow)
    raw_blob_path: str | None = None
    content_hash: str | None = None


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
