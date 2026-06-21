"""Service Bus queue consumers."""

from __future__ import annotations

from webfeed_shared.contracts import IngestJob, ReportJob

from webfeed_platform.clients import servicebus_client
from webfeed_platform.config import get_settings
from webfeed_platform.observability import get_logger

from app.handlers import handle_ingest, handle_report

log = get_logger("webfeed-worker.consumers")


def consume_ingest_queue() -> None:
    settings = get_settings()
    with servicebus_client() as client:
        receiver = client.get_queue_receiver(settings.servicebus_ingest_queue)
        with receiver:
            for msg in receiver:
                try:
                    job = IngestJob.model_validate_json(str(msg))
                    handle_ingest(job)
                    receiver.complete_message(msg)
                except Exception:  # noqa: BLE001
                    log.exception("Ingest message failed; abandoning for retry")
                    receiver.abandon_message(msg)


def consume_report_queue() -> None:
    settings = get_settings()
    with servicebus_client() as client:
        receiver = client.get_queue_receiver(settings.servicebus_report_queue)
        with receiver:
            for msg in receiver:
                try:
                    job = ReportJob.model_validate_json(str(msg))
                    handle_report(job)
                    receiver.complete_message(msg)
                except Exception:  # noqa: BLE001
                    log.exception("Report message failed; abandoning for retry")
                    receiver.abandon_message(msg)
