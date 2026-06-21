"""Job handlers: execute ingest and report jobs end-to-end."""

from __future__ import annotations

from webfeed_shared.contracts import IngestJob, JobStatus, JobType, ReportJob

from webfeed_platform.observability import get_logger
from webfeed_domain import jobs as jobs_domain
from webfeed_domain import sources as sources_domain
from webfeed_domain.extraction import extract_from_html, normalize_text
from webfeed_domain.indexing import build_chunks, index_chunks
from webfeed_domain.ingestion import fetch_document_html, ingest_source
from webfeed_domain.reporting import generate_report, persist_report

log = get_logger("webfeed-worker.handlers")


def handle_ingest(job: IngestJob) -> None:
    """Fetch sources, extract content, chunk, embed and index."""
    jobs_domain.update_job_status(job.job_id, JobType.INGEST, JobStatus.RUNNING)
    try:
        sources = sources_domain.list_enabled_sources()
        if job.source_ids:
            wanted = set(job.source_ids)
            sources = [s for s in sources if s.id in wanted]

        total_chunks = 0
        for source in sources:
            documents = ingest_source(source)
            for doc in documents:
                html = fetch_document_html(doc)
                text = normalize_text(extract_from_html(html))
                chunks = build_chunks(doc, text)
                total_chunks += index_chunks(chunks)

        jobs_domain.update_job_status(
            job.job_id, JobType.INGEST, JobStatus.SUCCEEDED,
            result_ref=f"chunks={total_chunks}",
        )
        log.info("Ingest job %s done: %d chunks", job.job_id, total_chunks)
    except Exception as exc:  # noqa: BLE001
        jobs_domain.update_job_status(
            job.job_id, JobType.INGEST, JobStatus.FAILED, error=str(exc)
        )
        log.exception("Ingest job %s failed", job.job_id)
        raise


def handle_report(job: ReportJob) -> None:
    """Retrieve relevant content and generate a structured briefing report."""
    jobs_domain.update_job_status(job.job_id, JobType.REPORT, JobStatus.RUNNING)
    try:
        tags = [t for t in (job.filters.get("tags") or "").split(",") if t]
        report = generate_report(job.query, job.title, tags)
        blob_path = persist_report(report)
        jobs_domain.update_job_status(
            job.job_id, JobType.REPORT, JobStatus.SUCCEEDED, result_ref=report.report_id
        )
        log.info("Report job %s done: %s", job.job_id, blob_path)
    except Exception as exc:  # noqa: BLE001
        jobs_domain.update_job_status(
            job.job_id, JobType.REPORT, JobStatus.FAILED, error=str(exc)
        )
        log.exception("Report job %s failed", job.job_id)
        raise
