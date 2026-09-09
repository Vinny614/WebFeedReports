"""Conversational RAG over indexed content, streamed as Server-Sent Events."""

from __future__ import annotations

import json
from collections.abc import Iterator

from webfeed_shared.api_models import ChatMessage, SearchFilters

from webfeed_platform.clients import openai_client
from webfeed_platform.config import get_settings
from webfeed_platform.observability import get_logger
from webfeed_domain.query import search

log = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are a research assistant for a briefing platform. Answer the user's "
    "question using ONLY the provided sources (drawn from RSS feeds, web pages "
    "and APIs). If the sources do not contain the answer, say so plainly rather "
    "than guessing. Be concise, cite the source id inline as [source_id] when you "
    "use a source, and never invent facts or URLs."
)


def _latest_user_message(messages: list[ChatMessage]) -> str:
    for m in reversed(messages):
        if m.role == "user":
            return m.content
    return ""


def _retrieve(query: str, filters: SearchFilters) -> list[dict]:
    hits = search(
        query,
        top=8,
        source_ids=filters.source_ids,
        date_from=filters.date_from,
        date_to=filters.date_to,
        tags=filters.tags,
    )
    return [
        {"source_id": h.source_id, "title": h.title, "url": h.url, "text": h.snippet}
        for h in hits
    ]


def _citations(context: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for c in context:
        key = c.get("url") or c.get("source_id") or ""
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "source_id": c.get("source_id", ""),
                "title": c.get("title"),
                "url": c.get("url"),
            }
        )
    return out


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def stream_chat(messages: list[ChatMessage], filters: SearchFilters) -> Iterator[str]:
    """Yield SSE frames: the sources used, then answer deltas, then a done marker."""
    settings = get_settings()
    query = _latest_user_message(messages)
    context = _retrieve(query, filters) if query else []

    yield _sse({"type": "sources", "items": _citations(context)})

    grounding = (
        "Sources you may use (JSON):\n"
        f"{json.dumps(context, indent=2)}\n\n"
        "Ground your answer in these sources only."
    )
    chat_messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "system", "content": grounding},
        *[{"role": m.role, "content": m.content} for m in messages],
    ]

    try:
        stream = openai_client().chat.completions.create(
            model=settings.openai_chat_deployment,
            messages=chat_messages,
            temperature=0.2,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield _sse({"type": "delta", "text": delta.content})
    except Exception as exc:  # surface failures to the client instead of hanging
        log.exception("Chat generation failed")
        yield _sse({"type": "error", "message": str(exc)})
        return

    yield _sse({"type": "done"})
