"""HTML/content extraction and normalization.

Converts raw RSS entries and HTML pages into clean, structured text. Kept fully
in Python (not in Azure AI Search skillsets) so the pipeline is testable and
controlled.
"""

from __future__ import annotations

import hashlib

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


def normalize_text(text: str) -> str:
    """Collapse whitespace and trim."""
    return " ".join(text.split()).strip()
