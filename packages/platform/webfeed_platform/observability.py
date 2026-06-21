"""Logging and telemetry setup.

Uses Azure Monitor OpenTelemetry when a connection string is present; otherwise
falls back to structured stdout logging suitable for Container Apps log capture.
"""

from __future__ import annotations

import logging
import sys

from .config import get_settings

_configured = False


def configure_observability(service_name: str | None = None) -> None:
    global _configured
    if _configured:
        return

    settings = get_settings()
    name = service_name or settings.service_name

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
    )

    if settings.applicationinsights_connection_string:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(
                connection_string=settings.applicationinsights_connection_string,
                logger_name=name,
            )
        except ImportError:
            logging.getLogger(name).warning(
                "azure-monitor-opentelemetry not installed; using stdout logging only"
            )

    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
