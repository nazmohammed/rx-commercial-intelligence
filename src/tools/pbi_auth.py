"""Power BI service-principal authentication via MSAL."""

import os
import msal

_TOKEN_CACHE: dict = {}


def get_pbi_access_token() -> str:
    """Acquire a Power BI REST API access token using client credentials.

    Returns the bearer token string. Caches until expiry.
    """
    cached = _TOKEN_CACHE.get("token")
    if cached:
        return cached

    tenant_id = os.environ["PBI_TENANT_ID"]
    client_id = os.environ["PBI_CLIENT_ID"]
    client_secret = os.environ["PBI_CLIENT_SECRET"]

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )

    result = app.acquire_token_for_client(
        scopes=["https://analysis.windows.net/powerbi/api/.default"]
    )

    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "Unknown MSAL error"))
        raise RuntimeError(f"PBI auth failed: {error}")

    _TOKEN_CACHE["token"] = result["access_token"]
    return result["access_token"]
