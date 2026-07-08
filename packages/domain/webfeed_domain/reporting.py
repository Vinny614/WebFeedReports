"""Reporting: agent-style retrieval + Azure OpenAI structured briefing generation."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from webfeed_shared.api_models import (
    BriefingReport,
    ReportCitation,
    ReportItem,
    ReportSection,
    ReportTemplate,
    ReportTemplateSection,
    SearchFilters,
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


def _build_context(query: str, filters: SearchFilters) -> list[dict]:
    items = search(
        query,
        top=12,
        source_ids=filters.source_ids,
        date_from=filters.date_from,
        date_to=filters.date_to,
        tags=filters.tags,
    )
    return [
        {
            "source_id": it.source_id,
            "title": it.title,
            "url": it.url,
            "text": it.snippet,
        }
        for it in items
    ]


def generate_report(
    query: str, title: str | None, filters: SearchFilters
) -> BriefingReport:
    """Retrieve relevant content and generate a structured briefing report."""
    settings = get_settings()
    context = _build_context(query, filters)

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


# --- Templated (section-by-section) generation -------------------------------


def _complete_json(
    heading: str, instruction: str, schema: dict, context: list[dict]
) -> dict:
    """One focused JSON-mode completion for a single section."""
    settings = get_settings()
    user_prompt = (
        f"Section heading: {heading}\n"
        f"Instruction: {instruction}\n\n"
        f"Return strict JSON matching this schema: {json.dumps(schema)}\n\n"
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
    return json.loads(completion.choices[0].message.content or "{}")


def _section_query(base_query: str, section: ReportTemplateSection) -> str:
    parts = [section.query or base_query, section.heading]
    if section.guidance:
        parts.append(section.guidance)
    return " ".join(p for p in parts if p).strip()


def _summarise_prior(sections: list[ReportSection]) -> str:
    lines: list[str] = []
    for sec in sections:
        lines.append(f"## {sec.heading}")
        for it in sec.items:
            lines.append(f"- {it.title} ({it.source or ''}): {it.summary}")
    return "\n".join(lines)


def _generate_section(
    base_query: str,
    section: ReportTemplateSection,
    seen_urls: set[str],
    filters: SearchFilters,
    prior_sections: list[ReportSection] | None = None,
) -> ReportSection:
    """Retrieve for one heading and produce that section in the requested style."""
    hits = search(
        _section_query(base_query, section),
        top=8,
        source_ids=filters.source_ids,
        tags=list(dict.fromkeys([*filters.tags, *section.tags])),
        date_from=filters.date_from,
        date_to=filters.date_to,
    )
    context = [
        {"source_id": h.source_id, "title": h.title, "url": h.url, "text": h.snippet}
        for h in hits
    ]
    # Map each retrieved article URL to its published date so we can attach it
    # to the LLM-produced items (which only carry title/source/url/summary).
    published_by_url = {h.url: h.published_at for h in hits if h.url and h.published_at}

    if section.style == "items":
        schema = {
            "items": [
                {
                    "title": "string",
                    "source": "string",
                    "url": "string",
                    "summary": "string",
                }
            ]
        }
        guidance = section.guidance or (
            "Cover the most newsworthy developments for this heading."
        )
        instruction = (
            f"{guidance}\n\n"
            "Extract every distinct news story contained in the provided sources "
            "that fits this heading. For each item provide: the headline/title, "
            "the publication or source name, the exact url taken from that source "
            "(never invent or alter a url), and a 1-2 sentence summary drawn only "
            "from the source text. Prefer specific article headlines; if a source "
            "is a listing or newsroom page, still include its most prominent story "
            "using that page's url. Only omit a source if it contains no story at "
            "all (pure navigation). Return items in order of relevance."
        )
        payload = _complete_json(section.heading, instruction, schema, context)
        raw_items = payload.get("items")
        if isinstance(raw_items, dict):
            raw_items = [raw_items]
        elif not isinstance(raw_items, list):
            raw_items = []
        items: list[ReportItem] = []
        for it in raw_items:
            if not isinstance(it, dict):
                continue
            url = (it.get("url") or "").strip() or None
            if url and url in seen_urls:
                continue  # cross-section dedupe
            if url:
                seen_urls.add(url)
            title = (it.get("title") or "").strip()
            if not title:
                continue
            items.append(
                ReportItem(
                    title=title,
                    url=url,
                    source=(it.get("source") or "").strip() or None,
                    published_at=published_by_url.get(url) if url else None,
                    summary=(it.get("summary") or "").strip(),
                )
            )
        return ReportSection(heading=section.heading, style="items", items=items)

    # narrative
    schema = {"content": "string"}
    instruction = (
        section.guidance
        or "Write 3-4 concise paragraphs summarising the key themes."
    ) + " Base every statement on the provided material; do not invent facts."
    if prior_sections:
        instruction += (
            "\n\nSummarise the following already-written sections:\n"
            + _summarise_prior(prior_sections)
        )
    payload = _complete_json(section.heading, instruction, schema, context)
    return ReportSection(
        heading=section.heading,
        style="narrative",
        content=(payload.get("content") or "").strip(),
    )


def generate_templated_report(
    base_query: str,
    title: str | None,
    template: ReportTemplate,
    filters: SearchFilters,
) -> BriefingReport:
    """Generate a report section-by-section from a template (sequential).

    Item sections are generated first so that any narrative/summary section can
    be written with visibility of the item output. Each section is resilient:
    a failure or empty result is skipped rather than aborting the report.
    """
    seen_urls: set[str] = set()
    item_secs = [s for s in template.sections if s.style == "items"]
    narrative_secs = [s for s in template.sections if s.style == "narrative"]
    generated: dict[str, ReportSection] = {}

    for s in item_secs:
        try:
            generated[s.heading] = _generate_section(base_query, s, seen_urls, filters)
        except Exception as exc:  # noqa: BLE001
            log.warning("Report section '%s' failed: %s", s.heading, exc)

    prior = [generated[s.heading] for s in item_secs if s.heading in generated]
    for s in narrative_secs:
        try:
            generated[s.heading] = _generate_section(
                base_query, s, seen_urls, filters, prior_sections=prior
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Report section '%s' failed: %s", s.heading, exc)

    ordered: list[ReportSection] = []
    for s in template.sections:
        sec = generated.get(s.heading)
        if sec is None:
            continue
        # Keep item sections even when empty so the user's chosen headings are
        # always shown (the UI renders an explicit empty state). Drop only
        # narrative sections that produced no prose.
        if sec.style == "narrative" and not sec.content:
            continue
        ordered.append(sec)

    citations = [
        ReportCitation(source_id=i.source or "", title=i.title, url=i.url)
        for sec in ordered
        for i in sec.items
        if i.url
    ]
    return BriefingReport(
        report_id=str(uuid.uuid4()),
        title=title or template.name or base_query,
        query=base_query,
        summary="",
        sections=ordered,
        citations=citations,
    )


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
