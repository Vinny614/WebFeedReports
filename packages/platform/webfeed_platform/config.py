"""Centralized configuration loaded from environment variables.

No secrets are stored here. All Azure access uses Managed Identity, so only
endpoints, resource names and deployment names are configured.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Identity (blank locally -> developer Entra sign-in via DefaultAzureCredential)
    azure_client_id: str | None = None

    # Storage
    storage_account_blob_url: str = ""
    storage_account_table_url: str = ""
    raw_container: str = "raw"
    reports_container: str = "reports"
    sources_container: str = "sources"
    sources_blob_name: str = "sources.yaml"
    templates_container: str = "report-templates"
    templates_blob_name: str = "templates.yaml"
    recent_headings_blob_name: str = "recent-headings.json"
    jobs_table: str = "jobs"
    sources_table: str = "sources"

    # Azure AI Search
    search_endpoint: str = ""
    search_index_name: str = "webfeed-chunks"

    # Azure OpenAI
    openai_endpoint: str = ""
    openai_api_version: str = "2024-06-01"
    openai_embed_deployment: str = "text-embedding-3-large"
    openai_chat_deployment: str = "gpt-4o"

    # Service Bus
    servicebus_fqdn: str = ""
    servicebus_ingest_queue: str = "ingest-jobs"
    servicebus_report_queue: str = "report-jobs"

    # Telemetry
    applicationinsights_connection_string: str | None = None

    # Service identity (for logging/telemetry role name)
    service_name: str = "webfeed"


@lru_cache
def get_settings() -> Settings:
    return Settings()
