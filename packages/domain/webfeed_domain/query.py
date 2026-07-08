"""Query / retrieval against Azure AI Search (hybrid: keyword + vector)."""

from __future__ import annotations

from datetime import datetime

from azure.search.documents.models import VectorizedQuery
from webfeed_shared.api_models import QueryResultItem

from webfeed_platform.clients import search_client
from webfeed_domain.indexing import embed_texts


def _build_filter(
    source_ids: list[str],
    date_from: datetime | None,
    date_to: datetime | None,
) -> str | None:
    """Compose an OData filter from company (source_id) and date-range filters."""
    clauses: list[str] = []
    if source_ids:
        ors = " or ".join(f"source_id eq '{s}'" for s in source_ids)
        clauses.append(f"({ors})")
    if date_from:
        clauses.append(f"published_at ge {date_from.isoformat()}")
    if date_to:
        clauses.append(f"published_at le {date_to.isoformat()}")
    return " and ".join(clauses) or None


def search(
    query: str,
    top: int = 10,
    source_ids: list[str] | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    tags: list[str] | None = None,
) -> list[QueryResultItem]:
    """Hybrid search: combines keyword and vector retrieval.

    ``source_ids`` restricts by company/source; ``date_from``/``date_to`` bound
    ``published_at``. ``tags`` is a legacy alias treated as additional
    source_id filters (the index has no separate tags field yet).
    """
    src = list(dict.fromkeys([*(source_ids or []), *(tags or [])]))
    embedding = embed_texts([query])[0]
    vector_query = VectorizedQuery(vector=embedding, k_nearest_neighbors=top, fields="embedding")

    results = search_client().search(
        search_text=query,
        vector_queries=[vector_query],
        filter=_build_filter(src, date_from, date_to),
        top=top,
    )

    items: list[QueryResultItem] = []
    for r in results:
        text = r.get("text", "")
        items.append(
            QueryResultItem(
                chunk_id=r["id"],
                document_id=r.get("document_id", ""),
                source_id=r.get("source_id", ""),
                score=r.get("@search.score", 0.0),
                title=r.get("title") or None,
                url=r.get("url") or None,
                published_at=r.get("published_at") or None,
                snippet=text[:400],
            )
        )
    return items
