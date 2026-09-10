"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from webfeed_shared.api_models import SourceHealth, SourceHealthSummary

from webfeed_domain import source_health as source_health_domain
from webfeed_domain import sources as sources_domain

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/sources", response_model=list[SourceHealth])
def source_health() -> list[SourceHealth]:
    """Return current health, including never-run configured sources."""
    stored = {h.source_id: h for h in source_health_domain.list_source_health()}
    return [
        stored.get(source.id, SourceHealth(source_id=source.id))
        for source in sources_domain.list_enabled_sources()
    ]


@router.get("/health/sources/{source_id}", response_model=SourceHealth)
def source_health_detail(source_id: str) -> SourceHealth:
    configured = {source.id for source in sources_domain.list_enabled_sources()}
    if source_id not in configured:
        raise HTTPException(status_code=404, detail="Source not found")
    return source_health_domain.get_source_health(source_id) or SourceHealth(
        source_id=source_id
    )


@router.get("/health/summary", response_model=SourceHealthSummary)
def source_health_summary() -> SourceHealthSummary:
    items = source_health()
    counts = {status: 0 for status in ("healthy", "degraded", "failed", "never")}
    for item in items:
        counts[item.status] += 1
    return SourceHealthSummary(total=len(items), **counts)


@router.get("/")
def root() -> dict[str, str]:
    return {"service": "webfeed-api", "status": "ok"}
