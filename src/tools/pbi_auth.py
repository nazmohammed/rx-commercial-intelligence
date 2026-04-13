"""Power BI authentication via DefaultAzureCredential (managed identity).

Uses the same system-assigned managed identity that calls Foundry agents.
In production (Container Apps) this uses the MI; locally it falls back to
Azure CLI / VS Code / environment credentials.
"""

from azure.identity.aio import DefaultAzureCredential

PBI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"

# Module-level credential — reused across requests (handles token caching internally)
_credential: DefaultAzureCredential | None = None


def _get_credential() -> DefaultAzureCredential:
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


async def get_pbi_access_token() -> str:
    """Acquire a Power BI REST API access token using DefaultAzureCredential.

    Returns the bearer token string. The credential handles caching internally.
    """
    credential = _get_credential()
    token = await credential.get_token(PBI_SCOPE)
    return token.token


async def close_credential() -> None:
    """Close the credential when shutting down."""
    global _credential
    if _credential is not None:
        await _credential.close()
        _credential = None
