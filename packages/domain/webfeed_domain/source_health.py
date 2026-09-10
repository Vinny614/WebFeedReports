"""Persistent current health for configured ingestion sources."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import cast

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from webfeed_shared.api_models import SourceHealth, SourceHealthStatus

from webfeed_platform.clients import table_service_client
from webfeed_platform.config import get_settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _table():
    settings = get_settings()
    service = table_service_client()
    try:
        service.create_table(settings.sources_health_table)
    except ResourceExistsError:
        pass
    return service.get_table_client(settings.sources_health_table)


def _from_entity(entity: dict) -> SourceHealth:
    return SourceHealth(
        source_id=entity["RowKey"],
        status=cast(SourceHealthStatus, entity.get("status") or "never"),
        last_attempt_at=entity.get("last_attempt_at") or None,
        last_success_at=entity.get("last_success_at") or None,
        newest_published_at=entity.get("newest_published_at") or None,
        success_count=int(entity.get("success_count", 0)),
        failure_count=int(entity.get("failure_count", 0)),
        consecutive_failures=int(entity.get("consecutive_failures", 0)),
        document_count=int(entity.get("document_count", 0)),
        indexed_document_count=int(entity.get("indexed_document_count", 0)),
        chunk_count=int(entity.get("chunk_count", 0)),
        warnings=json.loads(entity.get("warnings") or "[]"),
        latest_error=entity.get("latest_error") or None,
    )


def get_source_health(source_id: str) -> SourceHealth | None:
    try:
        entity = _table().get_entity(partition_key="source", row_key=source_id)
    except ResourceNotFoundError:
        return None
    return _from_entity(dict(entity))


def list_source_health() -> list[SourceHealth]:
    try:
        entities = _table().query_entities("PartitionKey eq 'source'")
        return [_from_entity(dict(entity)) for entity in entities]
    except ResourceNotFoundError:
        return []


def record_source_health(
    source_id: str,
    *,
    status: SourceHealthStatus,
    document_count: int = 0,
    indexed_document_count: int = 0,
    chunk_count: int = 0,
    newest_published_at: datetime | None = None,
    warnings: list[str] | None = None,
    error: str | None = None,
) -> SourceHealth:
    """Replace the current source-health row while preserving counters."""
    previous = get_source_health(source_id) or SourceHealth(source_id=source_id)
    attempted_at = _utcnow()
    succeeded = status in {"healthy", "degraded"}
    health = SourceHealth(
        source_id=source_id,
        status=status,
        last_attempt_at=attempted_at,
        last_success_at=attempted_at if succeeded else previous.last_success_at,
        newest_published_at=(
            newest_published_at
            if status != "failed"
            else previous.newest_published_at
        ),
        success_count=previous.success_count + int(succeeded),
        failure_count=previous.failure_count + int(status == "failed"),
        consecutive_failures=(
            previous.consecutive_failures + 1 if status == "failed" else 0
        ),
        document_count=document_count,
        indexed_document_count=indexed_document_count,
        chunk_count=chunk_count,
        warnings=list(dict.fromkeys(warnings or [])),
        latest_error=(error or "")[:1000] or None,
    )
    entity = {
        "PartitionKey": "source",
        "RowKey": source_id,
        "status": health.status,
        "last_attempt_at": health.last_attempt_at.isoformat(),
        "last_success_at": health.last_success_at.isoformat() if health.last_success_at else "",
        "newest_published_at": (
            health.newest_published_at.isoformat() if health.newest_published_at else ""
        ),
        "success_count": health.success_count,
        "failure_count": health.failure_count,
        "consecutive_failures": health.consecutive_failures,
        "document_count": health.document_count,
        "indexed_document_count": health.indexed_document_count,
        "chunk_count": health.chunk_count,
        "warnings": json.dumps(health.warnings),
        "latest_error": health.latest_error or "",
    }
    _table().upsert_entity(entity)
    return health
