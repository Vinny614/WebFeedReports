"""Scheduled polling: periodically enqueue ingestion jobs."""

from __future__ import annotations

import uuid

from apscheduler.schedulers.background import BackgroundScheduler

from webfeed_platform.observability import get_logger
from webfeed_shared.contracts import IngestJob, JobType
from webfeed_domain import jobs as jobs_domain

log = get_logger("webfeed-worker.scheduler")

# Default polling cadence (matches sources.yaml default). For per-source cron,
# extend this to read schedules from the registry.
_DEFAULT_INTERVAL_HOURS = 6


def _enqueue_full_ingest() -> None:
    job_id = str(uuid.uuid4())
    jobs_domain.create_job_record(job_id, JobType.INGEST)
    jobs_domain.enqueue_ingest(IngestJob(job_id=job_id, source_ids=[]))
    log.info("Scheduled ingest job %s enqueued", job_id)


def schedule_polling(scheduler: BackgroundScheduler) -> None:
    scheduler.add_job(
        _enqueue_full_ingest,
        trigger="interval",
        hours=_DEFAULT_INTERVAL_HOURS,
        id="full-ingest",
        replace_existing=True,
    )
