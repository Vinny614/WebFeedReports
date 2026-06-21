"""Job lifecycle: enqueue to Service Bus and persist state in Table Storage."""

from __future__ import annotations

from datetime import datetime, timezone

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.servicebus import ServiceBusMessage
from webfeed_shared.contracts import IngestJob, JobRecord, JobStatus, JobType, ReportJob

from webfeed_platform.clients import servicebus_client, table_service_client
from webfeed_platform.config import get_settings
from webfeed_platform.observability import get_logger

log = get_logger(__name__)


def _table():
    settings = get_settings()
    svc = table_service_client()
    try:
        svc.create_table(settings.jobs_table)
    except ResourceExistsError:
        pass
    return svc.get_table_client(settings.jobs_table)


def _to_entity(record: JobRecord) -> dict:
    return {
        "PartitionKey": record.type.value,
        "RowKey": record.job_id,
        "status": record.status.value,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "error": record.error or "",
        "result_ref": record.result_ref or "",
    }


def create_job_record(job_id: str, job_type: JobType) -> JobRecord:
    record = JobRecord(job_id=job_id, type=job_type, status=JobStatus.QUEUED)
    _table().upsert_entity(_to_entity(record))
    return record


def update_job_status(
    job_id: str,
    job_type: JobType,
    status: JobStatus,
    error: str | None = None,
    result_ref: str | None = None,
) -> None:
    table = _table()
    entity = table.get_entity(job_type.value, job_id)
    entity["status"] = status.value
    entity["updated_at"] = datetime.now(timezone.utc).isoformat()
    if error is not None:
        entity["error"] = error
    if result_ref is not None:
        entity["result_ref"] = result_ref
    table.update_entity(entity)


def get_job_record(job_id: str, job_type: JobType) -> JobRecord | None:
    try:
        e = _table().get_entity(job_type.value, job_id)
    except ResourceNotFoundError:
        return None
    return JobRecord(
        job_id=e["RowKey"],
        type=JobType(e["PartitionKey"]),
        status=JobStatus(e["status"]),
        created_at=datetime.fromisoformat(e["created_at"]),
        updated_at=datetime.fromisoformat(e["updated_at"]),
        error=e.get("error") or None,
        result_ref=e.get("result_ref") or None,
    )


def enqueue_ingest(job: IngestJob) -> None:
    settings = get_settings()
    with servicebus_client() as client:
        sender = client.get_queue_sender(settings.servicebus_ingest_queue)
        with sender:
            sender.send_messages(ServiceBusMessage(job.model_dump_json()))
    log.info("Enqueued ingest job %s", job.job_id)


def enqueue_report(job: ReportJob) -> None:
    settings = get_settings()
    with servicebus_client() as client:
        sender = client.get_queue_sender(settings.servicebus_report_queue)
        with sender:
            sender.send_messages(ServiceBusMessage(job.model_dump_json()))
    log.info("Enqueued report job %s", job.job_id)
