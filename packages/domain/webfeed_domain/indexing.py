"""Chunking, embeddings and Azure AI Search indexing."""

from __future__ import annotations

from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from webfeed_shared.models import Chunk, Document

from webfeed_platform.clients import openai_client, search_client, search_index_client
from webfeed_platform.config import get_settings
from webfeed_platform.observability import get_logger

log = get_logger(__name__)

# text-embedding-3-large dimension
_EMBED_DIM = 3072


def chunk_text(text: str, max_chars: int = 2000, overlap: int = 200) -> list[str]:
    """Simple character-window chunking with overlap."""
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    resp = openai_client().embeddings.create(
        model=settings.openai_embed_deployment,
        input=texts,
    )
    return [d.embedding for d in resp.data]


def build_chunks(document: Document, text: str) -> list[Chunk]:
    parts = chunk_text(text)
    if not parts:
        return []
    embeddings = embed_texts(parts)
    chunks: list[Chunk] = []
    for i, (part, emb) in enumerate(zip(parts, embeddings, strict=False)):
        chunks.append(
            Chunk(
                id=f"{document.id}-{i}",
                document_id=document.id,
                source_id=document.source_id,
                ordinal=i,
                text=part,
                url=document.url,
                title=document.title,
                published_at=document.published_at,
                embedding=emb,
            )
        )
    return chunks


def ensure_index() -> None:
    """Create the search index if it does not exist."""
    settings = get_settings()
    client = search_index_client()
    existing = {idx.name for idx in client.list_indexes()}
    if settings.search_index_name in existing:
        return

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="source_id", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="ordinal", type=SearchFieldDataType.Int32),
        SearchableField(name="text", type=SearchFieldDataType.String),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SimpleField(name="url", type=SearchFieldDataType.String),
        SimpleField(name="published_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=_EMBED_DIM,
            vector_search_profile_name="default-profile",
        ),
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="default-hnsw")],
        profiles=[VectorSearchProfile(name="default-profile", algorithm_configuration_name="default-hnsw")],
    )
    index = SearchIndex(name=settings.search_index_name, fields=fields, vector_search=vector_search)
    client.create_index(index)
    log.info("Created search index %s", settings.search_index_name)


def index_chunks(chunks: list[Chunk]) -> int:
    if not chunks:
        return 0
    docs = []
    for c in chunks:
        docs.append(
            {
                "id": c.id,
                "document_id": c.document_id,
                "source_id": c.source_id,
                "ordinal": c.ordinal,
                "text": c.text,
                "title": c.title or "",
                "url": str(c.url) if c.url else "",
                "published_at": c.published_at.isoformat() if c.published_at else None,
                "embedding": c.embedding,
            }
        )
    search_client().upload_documents(documents=docs)
    log.info("Indexed %d chunks", len(docs))
    return len(docs)
