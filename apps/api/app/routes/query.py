"""Query endpoint over indexed content."""

from __future__ import annotations

from fastapi import APIRouter
from webfeed_shared.api_models import QueryRequest, QueryResponse

from webfeed_domain.query import search

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
def run_query(request: QueryRequest) -> QueryResponse:
    items = search(
        request.query,
        top=request.top,
        source_ids=request.source_ids,
        date_from=request.date_from,
        date_to=request.date_to,
        tags=request.tags,
    )
    return QueryResponse(query=request.query, items=items)
