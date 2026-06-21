"""Worker entry point.

Responsibilities:
  - Seed the source registry from sources.yaml in Blob (Option B) on startup.
  - Ensure the search index exists.
  - Run scheduled polling (APScheduler) to enqueue ingest jobs.
  - Consume ingest and report jobs from Service Bus and execute them.

This keeps all long-running and scheduled work out of the API service.
"""

from __future__ import annotations

import threading

from apscheduler.schedulers.background import BackgroundScheduler

from webfeed_platform.observability import configure_observability, get_logger
from webfeed_domain import sources as sources_domain
from webfeed_domain.indexing import ensure_index

from app.consumers import consume_ingest_queue, consume_report_queue
from app.schedulers import schedule_polling

configure_observability("webfeed-worker")
log = get_logger("webfeed-worker")


def bootstrap() -> None:
    """One-time startup: seed registry from blob and ensure the index."""
    try:
        seeded = sources_domain.seed_registry(sources_domain.load_sources_from_blob())
        log.info("Bootstrap seeded %d sources", seeded)
    except Exception as exc:  # noqa: BLE001
        log.warning("Source seeding skipped: %s", exc)
    try:
        ensure_index()
    except Exception as exc:  # noqa: BLE001
        log.warning("Index ensure skipped: %s", exc)


def main() -> None:
    bootstrap()

    scheduler = BackgroundScheduler()
    schedule_polling(scheduler)
    scheduler.start()
    log.info("Scheduler started")

    # Run queue consumers in background threads.
    threading.Thread(target=consume_ingest_queue, daemon=True).start()
    threading.Thread(target=consume_report_queue, daemon=True).start()
    log.info("Queue consumers started")

    # Block main thread.
    threading.Event().wait()


if __name__ == "__main__":
    main()
