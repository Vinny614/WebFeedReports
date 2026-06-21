"""Job handlers: execute ingest and report jobs end-to-end."""

from __future__ import annotations

from webfeed_shared.contracts import IngestJob, JobStatus, JobType, ReportJob

from webfeed_platform.observability import get_logger
from webfeed_domain import jobs as jobs_domain
from webfeed_domain import sources as sources_domain
from webfeed_domain.indexing import build_chunks, index_chunks
from webfeed_domain.ingestion import extract_document_text, ingest_source
from webfeed_domain.reporting import generate_report, persist_report

log = get_logger("webfeed-worker.handlers")


def handle_ingest(job: IngestJob) -> None:
    """Fetch sources, extract content, chunk, embed and index."""
    jobs_domain.update_job_status(job.job_id, JobType.INGEST, JobStatus.RUNNING)
    try:
        # Re-seed the registry from sources.yaml in Blob so a manual refresh
        # always reflects the source-of-truth file, even if the worker started
        # before the blob was published.
        try:
            seeded = sources_domain.seed_registry(sources_domain.load_sources_from_blob())
            log.info("Ingest job %s seeded %d sources from blob", job.job_id, seeded)
        except Exception as exc:  # noqa: BLE001
            log.warning("Source re-seed skipped: %s", exc)

        sources = sources_domain.list_enabled_sources()
        if job.source_ids:
            wanted = set(job.source_ids)
            sources = [s for s in sources if s.id in wanted]

        total_chunks = 0
        for source in sources:
            documents = ingest_source(source)
            for doc in documents:
                text = extract_document_text(doc)
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
