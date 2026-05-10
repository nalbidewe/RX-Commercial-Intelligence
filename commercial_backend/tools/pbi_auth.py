"""Power BI authentication.

Two modes selectable via the ``PBI_AUTH_MODE`` env var:

* ``mi`` (default — legacy): use ``DefaultAzureCredential`` (Web App MI in
  prod, Azure CLI / VS Code locally). Fails with 401 in tenants that block
  service-principal calls to the PBI ``executeQueries`` API.

* ``user``: load an MSAL token cache from ``PBI_CACHE_PATH`` (default
  ``.pbi_cache.json`` at repo root) and silently refresh the cached
  refresh token to mint a delegated PBI access token. This authenticates
  as a real user, bypassing any SP-specific tenant gate.

The user-mode cache is bootstrapped once locally with::

    python bootstrap_pbi_token.py

and the resulting ``.pbi_cache.json`` is shipped with the deployment
(COPY in Dockerfile). The Web App's MI is **not** used for PBI in this
mode — it remains in use for Foundry / Cosmos / Key Vault.
"""

import asyncio
import os
from pathlib import Path

import msal
from azure.identity.aio import DefaultAzureCredential

PBI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"
_AUTH_MODE = os.environ.get("PBI_AUTH_MODE", "mi").lower()

# ── MI path (legacy) ───────────────────────────────────────────────────────
_credential: DefaultAzureCredential | None = None


def _get_credential() -> DefaultAzureCredential:
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


async def _get_mi_token() -> str:
    credential = _get_credential()
    token = await credential.get_token(PBI_SCOPE)
    return token.token


# ── User path (MSAL cached refresh token) ──────────────────────────────────
_cache: msal.SerializableTokenCache | None = None
_app: msal.PublicClientApplication | None = None
_lock = asyncio.Lock()


def _cache_path() -> Path:
    return Path(
        os.environ.get(
            "PBI_CACHE_PATH",
            str(Path(__file__).resolve().parents[2] / ".pbi_cache.json"),
        )
    )


def _load_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    p = _cache_path()
    if not p.exists():
        raise RuntimeError(
            f"PBI MSAL cache not found at {p}. "
            "Run `python bootstrap_pbi_token.py` locally and ship the resulting "
            ".pbi_cache.json with the deployment."
        )
    cache.deserialize(p.read_text(encoding="utf-8"))
    return cache


def _save_cache_if_changed() -> None:
    if _cache is not None and _cache.has_state_changed:
        _cache_path().write_text(_cache.serialize(), encoding="utf-8")


async def _get_user_token() -> str:
    global _cache, _app
    async with _lock:
        if _cache is None:
            _cache = _load_cache()
            _app = msal.PublicClientApplication(
                os.environ["PBI_USER_CLIENT_ID"],
                authority=(
                    "https://login.microsoftonline.com/"
                    f"{os.environ['PBI_USER_TENANT_ID']}"
                ),
                token_cache=_cache,
            )

        upn = os.environ.get("PBI_USER_UPN")
        accounts = _app.get_accounts(username=upn) if upn else _app.get_accounts()
        if not accounts:
            raise RuntimeError(
                "No cached account in MSAL cache. Re-run bootstrap_pbi_token.py."
            )

        # MSAL is sync — offload to default executor so we don't block the loop
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _app.acquire_token_silent([PBI_SCOPE], account=accounts[0]),
        )
        if not result or "access_token" not in result:
            raise RuntimeError(
                f"Silent token acquisition failed (refresh token expired or "
                f"revoked?). Re-run bootstrap_pbi_token.py. Detail: {result}"
            )
        _save_cache_if_changed()
        return result["access_token"]


# ── Public API ─────────────────────────────────────────────────────────────
async def get_pbi_access_token() -> str:
    """Acquire a PBI access token.

    Mode is selected at import time via the ``PBI_AUTH_MODE`` env var.
    """
    if _AUTH_MODE == "user":
        return await _get_user_token()
    return await _get_mi_token()


async def close_credential() -> None:
    """Close the MI credential when shutting down (no-op in user mode)."""
    global _credential
    if _credential is not None:
        await _credential.close()
        _credential = None
