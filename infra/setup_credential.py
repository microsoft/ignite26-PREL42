"""Credential selection shared by the setup scripts.

The Skillable lab runs the setup scripts as a service principal, passed in through AZURE_CLIENT_ID,
AZURE_CLIENT_SECRET, and AZURE_TENANT_ID. A self-deployment runs them with the azd sign-in.
"""

import os

from azure.identity import AzureDeveloperCliCredential, ClientSecretCredential
from azure.identity.aio import AzureDeveloperCliCredential as AsyncAzureDeveloperCliCredential
from azure.identity.aio import ClientSecretCredential as AsyncClientSecretCredential


def uses_service_principal() -> bool:
    """Return whether a service principal secret is available in the environment."""
    return bool(os.getenv("AZURE_CLIENT_ID") and os.getenv("AZURE_CLIENT_SECRET"))


def _service_principal_args(tenant_id: str | None) -> tuple[str, str, str]:
    tenant = tenant_id or os.environ["AZURE_TENANT_ID"]
    return (tenant, os.environ["AZURE_CLIENT_ID"], os.environ["AZURE_CLIENT_SECRET"])


def get_credential(tenant_id: str | None = None) -> ClientSecretCredential | AzureDeveloperCliCredential:
    """Return the service principal credential when configured, otherwise the azd credential."""
    if uses_service_principal():
        return ClientSecretCredential(*_service_principal_args(tenant_id))
    return AzureDeveloperCliCredential(tenant_id=tenant_id or "")


def get_async_credential(
    tenant_id: str | None = None,
) -> AsyncClientSecretCredential | AsyncAzureDeveloperCliCredential:
    """Async variant of get_credential."""
    if uses_service_principal():
        return AsyncClientSecretCredential(*_service_principal_args(tenant_id))
    return AsyncAzureDeveloperCliCredential(tenant_id=tenant_id or "")
