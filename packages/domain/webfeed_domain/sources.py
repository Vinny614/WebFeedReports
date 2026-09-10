"""Source loading, validation and registry.

The sources file (config/sources.yaml) is the declarative seed list. It is
published to Blob Storage at deploy time (Option B) and loaded here by the worker,
which seeds the source registry in Table Storage. The registry is the runtime
source of truth.
"""

from __future__ import annotations

import json

import yaml
from azure.core.exceptions import ResourceExistsError
from webfeed_shared.models import CrawlOptions, Source

from webfeed_platform.clients import blob_service_client, table_service_client
from webfeed_platform.config import get_settings
from webfeed_platform.observability import get_logger

log = get_logger(__name__)


def parse_sources(raw_yaml: str) -> list[Source]:
    """Parse and validate the sources YAML into typed Source models."""
    data = yaml.safe_load(raw_yaml) or {}
    defaults = data.get("defaults", {}) or {}
    sources: list[Source] = []
    for entry in data.get("sources", []) or []:
        merged = {**defaults, **entry}
        sources.append(Source.model_validate(merged))
    return sources


def load_sources_from_blob() -> list[Source]:
    """Read config/sources.yaml from the sources blob container."""
    settings = get_settings()
    container = blob_service_client().get_container_client(settings.sources_container)
    blob = container.get_blob_client(settings.sources_blob_name)
    raw = blob.download_blob().readall().decode("utf-8")
    return parse_sources(raw)


def seed_registry(sources: list[Source]) -> int:
    """Upsert sources into the Table Storage registry. Returns count upserted."""
    settings = get_settings()
    svc = table_service_client()
    try:
        svc.create_table(settings.sources_table)
    except ResourceExistsError:
        pass
    table = svc.get_table_client(settings.sources_table)
    count = 0
    for source in sources:
        entity = {
            "PartitionKey": "source",
            "RowKey": source.id,
            "type": source.type.value,
            "url": str(source.url),
            "enabled": source.enabled,
            "schedule": source.schedule or "",
            "tags": ",".join(source.tags),
            "crawl": source.crawl.model_dump_json() if source.crawl else "",
            "content_mode": source.content_mode,
            "expected_host": source.expected_host or "",
            "expected_text": source.expected_text or "",
            "min_documents": source.min_documents,
            "min_text_chars": source.min_text_chars,
            "max_age_days": source.max_age_days if source.max_age_days is not None else "",
        }
        table.upsert_entity(entity)
        count += 1
    log.info("Seeded %d sources into registry", count)
    return count


def list_enabled_sources() -> list[Source]:
    """Return enabled sources from the registry."""
    settings = get_settings()
    table = table_service_client().get_table_client(settings.sources_table)
    result: list[Source] = []
    for e in table.list_entities():
        if not e.get("enabled", True):
            continue
        tags = [t for t in (e.get("tags") or "").split(",") if t]
        crawl_raw = e.get("crawl") or ""
        crawl = CrawlOptions.model_validate(json.loads(crawl_raw)) if crawl_raw else None
        result.append(
            Source(
                id=e["RowKey"],
                type=e["type"],
                url=e["url"],
                enabled=e.get("enabled", True),
                schedule=e.get("schedule") or None,
                tags=tags,
                crawl=crawl,
                content_mode=e.get("content_mode") or "auto",
                expected_host=e.get("expected_host") or None,
                expected_text=e.get("expected_text") or None,
                min_documents=int(e.get("min_documents", 1)),
                min_text_chars=int(e.get("min_text_chars", 100)),
                max_age_days=(
                    int(e["max_age_days"])
                    if e.get("max_age_days") not in (None, "")
                    else (None if "max_age_days" in e else 45)
                ),
            )
        )
    return result
