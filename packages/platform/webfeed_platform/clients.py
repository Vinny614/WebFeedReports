"""Central factory for Azure SDK clients.

All clients are constructed from the shared Managed Identity credential. This is
the only place SDK clients are instantiated, so authentication and endpoint wiring
stay consistent across the API and worker services.
"""

from __future__ import annotations

from functools import lru_cache

from azure.data.tables import TableServiceClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.servicebus import ServiceBusClient
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI

from .config import Settings, get_settings
from .identity import get_credential, get_openai_token_provider


@lru_cache
def blob_service_client() -> BlobServiceClient:
    settings = get_settings()
    return BlobServiceClient(
        account_url=settings.storage_account_blob_url,
        credential=get_credential(),
    )


@lru_cache
def table_service_client() -> TableServiceClient:
    settings = get_settings()
    return TableServiceClient(
        endpoint=settings.storage_account_table_url,
        credential=get_credential(),
    )


def search_client(index_name: str | None = None) -> SearchClient:
    settings = get_settings()
    return SearchClient(
        endpoint=settings.search_endpoint,
        index_name=index_name or settings.search_index_name,
        credential=get_credential(),
    )


def search_index_client() -> SearchIndexClient:
    settings = get_settings()
    return SearchIndexClient(
        endpoint=settings.search_endpoint,
        credential=get_credential(),
    )


def servicebus_client() -> ServiceBusClient:
    settings = get_settings()
    return ServiceBusClient(
        fully_qualified_namespace=settings.servicebus_fqdn,
        credential=get_credential(),
    )


@lru_cache
def openai_client() -> AzureOpenAI:
    settings: Settings = get_settings()
    return AzureOpenAI(
        azure_endpoint=settings.openai_endpoint,
        api_version=settings.openai_api_version,
        azure_ad_token_provider=get_openai_token_provider(),
    )
