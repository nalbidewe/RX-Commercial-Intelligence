"""User identity resolver.

Resolves the signed-in user's UPN from one of three sources, tried in order:

1. Azure Container Apps Easy Auth headers (original deployment target):
       X-MS-CLIENT-PRINCIPAL-NAME / X-MS-CLIENT-PRINCIPAL-ID

2. X-User-UPN header — set by the React SPA after it retrieves the UPN from
   /api/commercial/me (used when running inside the Chainlit deployment where
   Easy Auth is not in front).

3. LOCAL_DEV_UPN env var — local development fallback.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Request


HEADER_UPN = "x-ms-client-principal-name"
HEADER_OID = "x-ms-client-principal-id"
HEADER_USER_UPN = "x-user-upn"


@dataclass
class AuthenticatedUser:
    upn: str
    oid: str | None = None
    is_local_dev: bool = False


def get_authenticated_user(request: Request) -> AuthenticatedUser:
    # 1. Easy Auth (Azure Container Apps)
    upn = request.headers.get(HEADER_UPN)
    oid = request.headers.get(HEADER_OID)
    if upn:
        return AuthenticatedUser(upn=upn, oid=oid, is_local_dev=False)

    # 2. X-User-UPN injected by the React SPA (Chainlit deployment)
    upn = request.headers.get(HEADER_USER_UPN)
    if upn:
        return AuthenticatedUser(upn=upn, oid=None, is_local_dev=False)

    # 3. Local dev fallback
    local_upn = os.environ.get("LOCAL_DEV_UPN")
    if local_upn:
        return AuthenticatedUser(upn=local_upn, oid=None, is_local_dev=True)

    return AuthenticatedUser(upn="", oid=None, is_local_dev=False)
