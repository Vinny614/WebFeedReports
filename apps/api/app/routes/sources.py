"""Source management endpoints.

Lists sources from the registry and triggers ingestion (manual re-run) by
enqueuing an ingest job. The worker performs the actual fetching/processing.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from webfeed_shared.api_models import JobSubmittedResponse
from webfeed_shared.contracts import IngestJob, JobType
from webfeed_shared.models import Source

from webfeed_domain import jobs as jobs_domain
from webfeed_domain import sources as sources_domain

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[Source])
def list_sources() -> list[Source]:
    return sources_domain.list_enabled_sources()


@router.post("/refresh", response_model=JobSubmittedResponse)
def refresh_sources(
    source_ids: list[str] | None = None, reset: bool = False
) -> JobSubmittedResponse:
    """Trigger a manual ingestion re-run for all or selected sources.

    When ``reset`` is true the worker purges and recreates the search index
    before ingesting, clearing any legacy/stale documents.
    """
    job_id = str(uuid.uuid4())
    jobs_domain.create_job_record(job_id, JobType.INGEST)
    jobs_domain.enqueue_ingest(
        IngestJob(job_id=job_id, source_ids=source_ids or [], reset=reset)
    )
    return JobSubmittedResponse(job_id=job_id, type=JobType.INGEST, status="queued")
