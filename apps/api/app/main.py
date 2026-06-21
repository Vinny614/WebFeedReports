"""FastAPI application entry point.

This service is an orchestration boundary only: it validates requests, submits
long-running work to Service Bus, and reads state/results back. No scraping,
embedding, or report generation happens inline here.
"""

from __future__ import annotations

from fastapi import FastAPI

from webfeed_platform.observability import configure_observability

from app.routes import health, jobs, query, reports, sources

configure_observability("webfeed-api")

app = FastAPI(
    title="WebFeedReports API",
    version="0.1.0",
    description="Query indexed content and generate briefing reports.",
)

app.include_router(health.router)
app.include_router(sources.router)
app.include_router(query.router)
app.include_router(reports.router)
app.include_router(jobs.router)
