"""Regression tests for source quality, retrieval grouping, and report grounding."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from webfeed_shared.api_models import (
    QueryResultItem,
    ReportTemplateSection,
    SearchFilters,
)
from webfeed_shared.models import Document, Source

from webfeed_domain import ingestion, query, reporting, sources


def test_broken_rss_placeholder_is_not_a_document(monkeypatch) -> None:
    source = Source(id="example", type="rss", url="https://example.test/feed")
    raw = b"<rss><channel><item></item></channel></rss>"
    monkeypatch.setattr(ingestion, "_fetch", lambda _url: raw)
    monkeypatch.setattr(ingestion, "_store_raw", lambda *_args: "raw/example/feed.xml")

    assert ingestion.ingest_source(source) == []


def test_article_mode_fetches_article_instead_of_feed_summary(monkeypatch) -> None:
    source = Source(
        id="example",
        type="rss",
        url="https://example.test/feed",
        content_mode="article",
    )
    document = Document(
        id="doc-1",
        source_id=source.id,
        url="https://example.test/news/1",
        title="News",
        content_html="<p>Short feed summary</p>",
        content_is_summary=True,
    )
    monkeypatch.setattr(
        ingestion,
        "fetch_document_html",
        lambda _document: "<main><p>Full article text from the linked page.</p></main>",
    )

    text, _ = ingestion.extract_document_content(document, source)

    assert "Full article text" in text
    assert "Short feed summary" not in text


def test_source_quality_options_round_trip_through_yaml() -> None:
    parsed = sources.parse_sources(
        """
        sources:
          - id: example
            type: rss
            url: https://example.test/feed
            content_mode: article
            expected_host: example.test
            expected_text: Aviation
            min_documents: 2
            min_text_chars: 250
            max_age_days: 14
        """
    )

    assert len(parsed) == 1
    assert parsed[0].content_mode == "article"
    assert parsed[0].expected_host == "example.test"
    assert parsed[0].expected_text == "Aviation"
    assert parsed[0].min_documents == 2
    assert parsed[0].min_text_chars == 250
    assert parsed[0].max_age_days == 14


def test_search_applies_top_after_distinct_document_grouping(monkeypatch) -> None:
    rows = [
        {
            "id": "chunk-a1",
            "document_id": "doc-a",
            "source_id": "source",
            "text": "A first",
            "url": "https://example.test/a",
            "@search.reranker_score": 3.0,
        },
        {
            "id": "chunk-a2",
            "document_id": "doc-a",
            "source_id": "source",
            "text": "A second",
            "url": "https://example.test/a",
            "@search.reranker_score": 2.9,
        },
        {
            "id": "chunk-b1",
            "document_id": "doc-b",
            "source_id": "source",
            "text": "B first",
            "url": "https://example.test/b",
            "@search.reranker_score": 2.8,
        },
    ]
    client = SimpleNamespace(search=lambda **_kwargs: rows)
    settings = SimpleNamespace(
        min_reranker_score=1.5,
        search_semantic_config="default",
    )
    monkeypatch.setattr(query, "embed_texts", lambda _texts: [[0.1, 0.2]])
    monkeypatch.setattr(query, "search_client", lambda: client)
    monkeypatch.setattr(query, "get_settings", lambda: settings)

    results = query.search("aviation", top=2)

    assert [result.document_id for result in results] == ["doc-a", "doc-b"]


def test_report_items_require_retrieved_normalized_url(monkeypatch) -> None:
    published = datetime(2025, 1, 2, tzinfo=timezone.utc)
    hit = QueryResultItem(
        chunk_id="chunk-1",
        document_id="doc-1",
        source_id="source-1",
        score=3.0,
        title="Grounded story",
        url="https://Example.test/story/?b=2&a=1",
        published_at=published,
        snippet="Grounded details",
    )
    monkeypatch.setattr(reporting, "search", lambda *_args, **_kwargs: [hit])
    monkeypatch.setattr(
        reporting,
        "_complete_json",
        lambda *_args, **_kwargs: {
            "items": [
                {
                    "title": "Grounded story",
                    "source": "Source One",
                    "url": "https://example.test/story?a=1&b=2#section",
                    "summary": "Grounded details",
                },
                {
                    "title": "Invented story",
                    "source": "Unknown",
                    "url": "https://invented.test/story",
                    "summary": "Not in retrieval",
                },
                {
                    "title": "Missing citation",
                    "source": "Unknown",
                    "summary": "No URL",
                },
            ]
        },
    )

    section = reporting._generate_section(
        "aviation",
        ReportTemplateSection(heading="News", style="items"),
        set(),
        SearchFilters(),
    )

    assert len(section.items) == 1
    assert section.items[0].url == str(hit.url)
    assert section.items[0].published_at == published
