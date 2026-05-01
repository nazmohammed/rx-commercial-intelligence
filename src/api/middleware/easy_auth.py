"""Easy Auth header reader.

Container Apps' built-in Microsoft identity provider (Easy Auth) injects
identity information into request headers after a successful sign-in:

    X-MS-CLIENT-PRINCIPAL-NAME = <user UPN>
    X-MS-CLIENT-PRINCIPAL-ID   = <user object id>

The frontend nginx sidecar reverse-proxies `/api/*` to localhost:8000
preserving these headers, so FastAPI can read them directly.

If the headers are missing (e.g. local dev without Easy Auth), this
middleware falls back to a configured `LOCAL_DEV_UPN` env var so we can
test against Power BI RLS using a real test account.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Request


HEADER_UPN = "x-ms-client-principal-name"
HEADER_OID = "x-ms-client-principal-id"


@dataclass
class AuthenticatedUser:
    upn: str
    oid: str | None = None
    is_local_dev: bool = False


def get_authenticated_user(request: Request) -> AuthenticatedUser:
    """Extract the signed-in user from Easy Auth headers.

    Falls back to LOCAL_DEV_UPN env var if headers are absent, which is the
    expected case when running uvicorn locally without Easy Auth in front.
    """
    upn = request.headers.get(HEADER_UPN)
    oid = request.headers.get(HEADER_OID)

    if upn:
        return AuthenticatedUser(upn=upn, oid=oid, is_local_dev=False)

    local_upn = os.environ.get("LOCAL_DEV_UPN")
    if local_upn:
        return AuthenticatedUser(upn=local_upn, oid=None, is_local_dev=True)

    # No Easy Auth header and no local override — treat as anonymous.
    # Routes that require auth should reject this explicitly.
    return AuthenticatedUser(upn="", oid=None, is_local_dev=False)
