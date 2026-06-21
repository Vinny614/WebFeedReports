"""Job status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from webfeed_shared.api_models import JobStatusResponse
from webfeed_shared.contracts import JobType

from webfeed_domain import jobs as jobs_domain

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_type}/{job_id}", response_model=JobStatusResponse)
def get_job(job_type: JobType, job_id: str) -> JobStatusResponse:
    record = jobs_domain.get_job_record(job_id, job_type)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        job_id=record.job_id,
        type=record.type,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        error=record.error,
        result_ref=record.result_ref,
    )
