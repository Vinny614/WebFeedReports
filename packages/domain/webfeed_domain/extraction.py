"""HTML/content extraction and normalization.

Converts raw RSS entries and HTML pages into clean, structured text. Kept fully
in Python (not in Azure AI Search skillsets) so the pipeline is testable and
controlled.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import trafilatura
from bs4 import BeautifulSoup


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_from_html(html: str) -> str:
    """Extract the main readable content from an HTML page."""
    extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
    if extracted:
        return extracted.strip()
    # Fallback: strip tags and collapse whitespace.
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())


def extract_date_from_html(html: str) -> datetime | None:
    """Best-effort publication date from an article page's metadata.

    Uses trafilatura's metadata extractor (which reads JSON-LD ``datePublished``,
    ``<meta property="article:published_time">``, Open Graph and common date
    patterns). Returns a timezone-aware UTC datetime, or ``None`` when no date
    can be determined. Rule-based only — no external/AI services.
    """
    try:
        meta = trafilatura.extract_metadata(html)
    except Exception:  # noqa: BLE001
        return None
    raw = getattr(meta, "date", None) if meta else None
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw))
    except ValueError:
        try:
            parsed = datetime.strptime(str(raw)[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def normalize_text(text: str) -> str:
    """Collapse whitespace and trim."""
    return " ".join(text.split()).strip()
