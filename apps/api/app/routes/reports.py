"""Report submission and retrieval endpoints.

Report generation is asynchronous: the API enqueues a report job and returns a
job id. Clients poll the jobs endpoint for status, then fetch the completed
report.
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException
from webfeed_shared.api_models import (
    BriefingReport,
    JobSubmittedResponse,
    RecentHeadingSet,
    ReportRequest,
    ReportTemplate,
)
from webfeed_shared.contracts import JobType, ReportJob

from webfeed_platform.clients import blob_service_client
from webfeed_platform.config import get_settings
from webfeed_domain import jobs as jobs_domain
from webfeed_domain import templates as templates_domain

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=JobSubmittedResponse)
def submit_report(request: ReportRequest) -> JobSubmittedResponse:
    job_id = str(uuid.uuid4())
    jobs_domain.create_job_record(job_id, JobType.REPORT)

    sections_payload = None
    if request.sections:
        sections_payload = [s.model_dump(mode="json") for s in request.sections]
        # Record the custom heading set in the recent (MRU) store; best-effort.
        try:
            templates_domain.record_recent_headings(
                request.sections, name=request.title
            )
        except Exception:  # noqa: BLE001
            pass

    jobs_domain.enqueue_report(
        ReportJob(
            job_id=job_id,
            query=request.query,
            title=request.title,
            filters={
                "tags": ",".join(request.tags),
                "source_ids": ",".join(request.source_ids),
                "date_from": request.date_from.isoformat() if request.date_from else "",
                "date_to": request.date_to.isoformat() if request.date_to else "",
            },
            template_id=request.template_id,
            sections=sections_payload,
        )
    )
    return JobSubmittedResponse(job_id=job_id, type=JobType.REPORT, status="queued")


@router.get("/templates", response_model=list[ReportTemplate])
def list_templates() -> list[ReportTemplate]:
    """Return the seeded report templates for the report builder."""
    return templates_domain.load_templates_from_blob()


@router.get("/recent-headings", response_model=list[RecentHeadingSet])
def list_recent_headings() -> list[RecentHeadingSet]:
    """Return the last few user-defined custom heading sets (newest first)."""
    return templates_domain.load_recent_headings()


@router.get("/{report_id}", response_model=BriefingReport)
def get_report(report_id: str) -> BriefingReport:
    settings = get_settings()
    container = blob_service_client().get_container_client(settings.reports_container)
    blob = container.get_blob_client(f"{report_id}.json")
    if not blob.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    data = json.loads(blob.download_blob().readall())
    return BriefingReport.model_validate(data)
