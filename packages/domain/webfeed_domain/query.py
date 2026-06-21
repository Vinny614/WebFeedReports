"""Query / retrieval against Azure AI Search (hybrid: keyword + vector)."""

from __future__ import annotations

from azure.search.documents.models import VectorizedQuery
from webfeed_shared.api_models import QueryResultItem

from webfeed_platform.clients import search_client
from webfeed_domain.indexing import embed_texts


def _build_filter(tags: list[str]) -> str | None:
    if not tags:
        return None
    # source_id is the closest filterable proxy for tags in this index.
    clauses = [f"source_id eq '{t}'" for t in tags]
    return " or ".join(clauses)


def search(query: str, top: int = 10, tags: list[str] | None = None) -> list[QueryResultItem]:
    """Hybrid search: combines keyword and vector retrieval."""
    embedding = embed_texts([query])[0]
    vector_query = VectorizedQuery(vector=embedding, k_nearest_neighbors=top, fields="embedding")

    results = search_client().search(
        search_text=query,
        vector_queries=[vector_query],
        filter=_build_filter(tags or []),
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
                snippet=text[:400],
            )
        )
    return items
