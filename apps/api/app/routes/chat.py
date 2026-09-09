"""Streaming conversational RAG endpoint (Server-Sent Events)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from webfeed_shared.api_models import ChatRequest, SearchFilters

from webfeed_domain.chat import stream_chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
def chat(request: ChatRequest) -> StreamingResponse:
    filters = SearchFilters(
        source_ids=request.source_ids,
        tags=request.tags,
        date_from=request.date_from,
        date_to=request.date_to,
    )
    return StreamingResponse(
        stream_chat(request.messages, filters),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
