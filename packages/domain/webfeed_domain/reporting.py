"""Reporting: agent-style retrieval + Azure OpenAI structured briefing generation."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from webfeed_shared.api_models import (
    BriefingReport,
    ReportCitation,
    ReportSection,
)

from webfeed_platform.clients import blob_service_client, openai_client
from webfeed_platform.config import get_settings
from webfeed_platform.observability import get_logger
from webfeed_domain.query import search

log = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are a briefing analyst. Using ONLY the provided sources, produce a concise, "
    "structured briefing. Return strict JSON matching the requested schema. Do not "
    "invent facts; cite source ids you used."
)

_SCHEMA_HINT = {
    "summary": "string",
    "sections": [{"heading": "string", "content": "string"}],
    "citations": [{"source_id": "string", "title": "string", "url": "string"}],
}


def _build_context(query: str, tags: list[str]) -> list[dict]:
    items = search(query, top=12, tags=tags)
    return [
        {
            "source_id": it.source_id,
            "title": it.title,
            "url": it.url,
            "text": it.snippet,
        }
        for it in items
    ]


def generate_report(query: str, title: str | None, tags: list[str]) -> BriefingReport:
    """Retrieve relevant content and generate a structured briefing report."""
    settings = get_settings()
    context = _build_context(query, tags)

    user_prompt = (
        f"Query: {query}\n\n"
        f"Schema: {json.dumps(_SCHEMA_HINT)}\n\n"
        f"Sources:\n{json.dumps(context, indent=2)}"
    )

    completion = openai_client().chat.completions.create(
        model=settings.openai_chat_deployment,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    payload = json.loads(completion.choices[0].message.content or "{}")

    report = BriefingReport(
        report_id=str(uuid.uuid4()),
        title=title or query,
        query=query,
        generated_at=datetime.now(timezone.utc),
        summary=payload.get("summary", ""),
        sections=[ReportSection(**s) for s in payload.get("sections", [])],
        citations=[ReportCitation(**c) for c in payload.get("citations", [])],
    )
    return report


def persist_report(report: BriefingReport) -> str:
    """Store the report JSON in Blob and return its blob path."""
    settings = get_settings()
    container = blob_service_client().get_container_client(settings.reports_container)
    try:
        container.create_container()
    except Exception:  # noqa: BLE001 - container may already exist
        pass
    path = f"{report.report_id}.json"
    container.get_blob_client(path).upload_blob(
        report.model_dump_json(indent=2), overwrite=True
    )
    return f"{settings.reports_container}/{path}"
