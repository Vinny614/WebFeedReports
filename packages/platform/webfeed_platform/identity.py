"""Single source of truth for credentials.

Every Azure SDK client in the system is built from the credential returned here.
In Azure Container Apps this resolves to the app's user-assigned managed identity
(via AZURE_CLIENT_ID); locally it resolves through the developer's Entra sign-in.
No API keys are ever used.
"""

from __future__ import annotations

from functools import lru_cache

from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from .config import get_settings

# Scope used for Azure OpenAI data-plane access via Entra ID.
COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"


@lru_cache
def get_credential() -> TokenCredential:
    settings = get_settings()
    kwargs: dict[str, str] = {}
    if settings.azure_client_id:
        # Bind to the specific user-assigned managed identity in the cloud.
        kwargs["managed_identity_client_id"] = settings.azure_client_id
    return DefaultAzureCredential(**kwargs)


def get_openai_token_provider():
    """Bearer token provider for the Azure OpenAI SDK (Entra auth, no keys)."""
    return get_bearer_token_provider(get_credential(), COGNITIVE_SERVICES_SCOPE)
