"""Report templates and the recent-headings (MRU) store.

Templates are declared in config/report_templates.yaml and published to Blob
Storage at deploy time (same Option B pattern as sources.yaml). The recent
headings store keeps the last few user-defined heading sets so they can be
reloaded from the report builder UI.
"""

from __future__ import annotations

import json

import yaml
from webfeed_shared.api_models import (
    RecentHeadingSet,
    ReportTemplate,
    ReportTemplateSection,
)

from webfeed_platform.clients import blob_service_client
from webfeed_platform.config import get_settings
from webfeed_platform.observability import get_logger

log = get_logger(__name__)

_MAX_RECENT = 5


def parse_templates(raw_yaml: str) -> list[ReportTemplate]:
    """Parse the templates YAML (a top-level list) into typed models."""
    data = yaml.safe_load(raw_yaml) or []
    if isinstance(data, dict):  # tolerate {"templates": [...]}
        data = data.get("templates", []) or []
    return [ReportTemplate.model_validate(entry) for entry in data]


def load_templates_from_blob() -> list[ReportTemplate]:
    """Read report templates from the templates blob. Returns [] if absent."""
    settings = get_settings()
    container = blob_service_client().get_container_client(settings.templates_container)
    blob = container.get_blob_client(settings.templates_blob_name)
    if not blob.exists():
        log.warning("Templates blob %s not found", settings.templates_blob_name)
        return []
    raw = blob.download_blob().readall().decode("utf-8")
    return parse_templates(raw)


def get_template(template_id: str) -> ReportTemplate | None:
    for tpl in load_templates_from_blob():
        if tpl.id == template_id:
            return tpl
    return None


def _signature(sections: list[ReportTemplateSection]) -> tuple:
    return tuple((s.heading.strip().lower(), s.style) for s in sections)


def _recent_blob():
    settings = get_settings()
    container = blob_service_client().get_container_client(settings.templates_container)
    try:
        container.create_container()
    except Exception:  # noqa: BLE001 - container may already exist
        pass
    return container.get_blob_client(settings.recent_headings_blob_name)


def load_recent_headings() -> list[RecentHeadingSet]:
    """Return the most-recently-used custom heading sets (newest first)."""
    blob = _recent_blob()
    if not blob.exists():
        return []
    try:
        data = json.loads(blob.download_blob().readall())
    except Exception:  # noqa: BLE001 - corrupt/empty blob
        return []
    return [RecentHeadingSet.model_validate(e) for e in data]


def record_recent_headings(
    sections: list[ReportTemplateSection], name: str | None = None
) -> None:
    """Prepend a heading set to the MRU store, dedupe, and cap at 5."""
    if not sections:
        return
    entry = RecentHeadingSet(name=name, sections=sections)
    sig = _signature(sections)
    existing = [r for r in load_recent_headings() if _signature(r.sections) != sig]
    updated = [entry, *existing][:_MAX_RECENT]
    payload = json.dumps([r.model_dump(mode="json") for r in updated], indent=2)
    _recent_blob().upload_blob(payload, overwrite=True)
