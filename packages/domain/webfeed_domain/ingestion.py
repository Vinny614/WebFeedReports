"""Ingestion: fetch RSS feeds and web pages, persist raw artifacts to Blob.

Raw payloads are stored immutably so processing can be re-run without re-fetching.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
from azure.core.exceptions import ResourceExistsError
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from webfeed_shared.models import Document, Source, SourceType

from webfeed_domain.extraction import extract_from_html, normalize_text
from webfeed_platform.clients import blob_service_client
from webfeed_platform.config import get_settings
from webfeed_platform.observability import get_logger

log = get_logger(__name__)

_USER_AGENT = "WebFeedReports/0.1 (+https://github.com/Vinny614/WebFeedReports)"

# File extensions that are never article pages.
_ASSET_SUFFIXES = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".css", ".js", ".pdf", ".zip", ".xml", ".json", ".mp4", ".mp3",
    ".woff", ".woff2", ".ttf",
)


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


def _entry_content_html(entry) -> str | None:
    """Best available content for an RSS entry.

    Prefers the full ``content:encoded`` body, then falls back to the entry
    summary/description. Returns ``None`` when the entry carries no content.
    """
    contents = entry.get("content")
    if contents:
        best = max((c.get("value", "") for c in contents), key=len, default="")
        if best.strip():
            return best
    summary = entry.get("summary")
    if summary and summary.strip():
        return summary
    return None


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
                content_html=_entry_content_html(entry),
            )
        )
    log.info("RSS %s -> %d documents", source.id, len(docs))
    return docs


def _discover_article_links(base_url: str, html: str, max_pages: int) -> list[tuple[str, str | None]]:
    """Find per-article links on a server-rendered listing page.

    Returns ``(url, title)`` pairs for same-host anchors that live *under* the
    listing path and are strictly deeper than it (i.e. article detail pages),
    skipping asset files and the listing/pagination page itself. Order is
    preserved and duplicates are removed. Capped at ``max_pages``.
    """
    base = urlparse(base_url)
    base_path = base.path.rstrip("/")
    base_depth = len([p for p in base_path.split("/") if p])

    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    results: list[tuple[str, str | None]] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https") or parsed.netloc != base.netloc:
            continue
        path = parsed.path.rstrip("/")
        if path.lower().endswith(_ASSET_SUFFIXES):
            continue
        # Must be under the listing path and strictly deeper (a detail page).
        if not path.startswith(base_path + "/"):
            continue
        if len([p for p in path.split("/") if p]) <= base_depth:
            continue
        clean = f"{parsed.scheme}://{parsed.netloc}{path}"
        if clean in seen:
            continue
        seen.add(clean)
        title = anchor.get("title") or normalize_text(anchor.get_text()) or None
        results.append((clean, title))
        if len(results) >= max_pages:
            break
    return results


def _ingest_web(source: Source) -> list[Document]:
    raw = _fetch(str(source.url))
    raw_path = _store_raw(source.id, "listing.html", raw)

    if source.crawl and source.crawl.depth >= 1:
        max_pages = source.crawl.max_pages or 25
        html = raw.decode("utf-8", errors="ignore")
        links = _discover_article_links(str(source.url), html, max_pages)
        if links:
            docs = [
                Document(
                    id=hashlib.sha1(url.encode("utf-8")).hexdigest(),
                    source_id=source.id,
                    url=url,
                    title=title,
                    raw_blob_path=raw_path,
                )
                for url, title in links
            ]
            log.info("WEB %s -> %d documents (crawled)", source.id, len(docs))
            return docs
        log.info("WEB %s -> crawl found no links, falling back to snapshot", source.id)

    doc_id = hashlib.sha1(str(source.url).encode("utf-8")).hexdigest()
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


def extract_document_text(document: Document) -> str:
    """Return clean text for a document.

    RSS entries carry their own curated content (a full article for feeds that
    publish ``content:encoded``, or a relevant summary for feeds that only
    publish teasers). That content is preferred and the landing page is *not*
    re-fetched, because many sources are single-page apps whose pages extract
    to generic navigation boilerplate rather than the item's content. The page
    is only fetched for web sources, or for an RSS entry that carried no usable
    content at all.
    """
    if document.content_html:
        text = normalize_text(extract_from_html(document.content_html))
        if text:
            return text
    return normalize_text(extract_from_html(fetch_document_html(document)))
