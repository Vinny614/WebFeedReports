"""Report submission and retrieval endpoints.

Report generation is asynchronous: the API enqueues a report job and returns a
job id. Clients poll the jobs endpoint for status, then fetch the completed
report.
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException
from webfeed_shared.api_models import BriefingReport, JobSubmittedResponse, ReportRequest
from webfeed_shared.contracts import JobType, ReportJob

from webfeed_platform.clients import blob_service_client
from webfeed_platform.config import get_settings
from webfeed_domain import jobs as jobs_domain

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=JobSubmittedResponse)
def submit_report(request: ReportRequest) -> JobSubmittedResponse:
    job_id = str(uuid.uuid4())
    jobs_domain.create_job_record(job_id, JobType.REPORT)
    jobs_domain.enqueue_report(
        ReportJob(
            job_id=job_id,
            query=request.query,
            title=request.title,
            filters={"tags": ",".join(request.tags)},
        )
    )
    return JobSubmittedResponse(job_id=job_id, type=JobType.REPORT, status="queued")


@router.get("/{report_id}", response_model=BriefingReport)
def get_report(report_id: str) -> BriefingReport:
    settings = get_settings()
    container = blob_service_client().get_container_client(settings.reports_container)
    blob = container.get_blob_client(f"{report_id}.json")
    if not blob.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    data = json.loads(blob.download_blob().readall())
    return BriefingReport.model_validate(data)
