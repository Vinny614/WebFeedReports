"""Ingestion: fetch RSS feeds and web pages, persist raw artifacts to Blob.

Raw payloads are stored immutably so processing can be re-run without re-fetching.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import feedparser
import httpx
from azure.core.exceptions import ResourceExistsError
from tenacity import retry, stop_after_attempt, wait_exponential
from webfeed_shared.models import Document, Source, SourceType

from webfeed_platform.clients import blob_service_client
from webfeed_platform.config import get_settings
from webfeed_platform.observability import get_logger

log = get_logger(__name__)

_USER_AGENT = "WebFeedReports/0.1 (+https://github.com/Vinny614/WebFeedReports)"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def _fetch(url: str) -> bytes:
    with httpx.Client(timeout=30, headers={"User-Agent": _USER_AGENT}) as client:
        resp = client.get(url, follow_redirects=True)
        resp.raise_for_status()
        return resp.content


def _ensure_container(name: str) -> None:
    try:
        blob_service_client().create_container(name)
    except ResourceExistsError:
        pass


def _store_raw(source_id: str, key: str, data: bytes) -> str:
    """Persist a raw artifact and return its blob path."""
    settings = get_settings()
    _ensure_container(settings.raw_container)
    blob_path = f"{source_id}/{key}"
    blob = blob_service_client().get_blob_client(settings.raw_container, blob_path)
    blob.upload_blob(data, overwrite=True)
    return f"{settings.raw_container}/{blob_path}"


def ingest_source(source: Source) -> list[Document]:
    """Fetch a single source and return the documents discovered."""
    if source.type == SourceType.RSS:
        return _ingest_rss(source)
    return _ingest_web(source)


def _ingest_rss(source: Source) -> list[Document]:
    raw = _fetch(str(source.url))
    raw_path = _store_raw(source.id, "feed.xml", raw)
    parsed = feedparser.parse(raw)
    docs: list[Document] = []
    for entry in parsed.entries:
        link = entry.get("link") or str(source.url)
        doc_id = hashlib.sha1(link.encode("utf-8")).hexdigest()
        published = None
        if entry.get("published_parsed"):
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        docs.append(
            Document(
                id=doc_id,
                source_id=source.id,
                url=link,
                title=entry.get("title"),
                published_at=published,
                raw_blob_path=raw_path,
            )
        )
    log.info("RSS %s -> %d documents", source.id, len(docs))
    return docs


def _ingest_web(source: Source) -> list[Document]:
    raw = _fetch(str(source.url))
    doc_id = hashlib.sha1(str(source.url).encode("utf-8")).hexdigest()
    raw_path = _store_raw(source.id, f"{doc_id}.html", raw)
    log.info("WEB %s -> 1 document", source.id)
    return [
        Document(
            id=doc_id,
            source_id=source.id,
            url=str(source.url),
            title=source.id,
            raw_blob_path=raw_path,
        )
    ]


def fetch_document_html(document: Document) -> str:
    """Fetch the full HTML for a document (used before extraction)."""
    return _fetch(str(document.url)).decode("utf-8", errors="ignore")
