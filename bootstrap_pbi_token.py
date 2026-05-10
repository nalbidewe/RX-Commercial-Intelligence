"""One-time bootstrap: sign in interactively via MSAL device code and persist
a Power BI token cache to ``.pbi_cache.json`` in the repo root.

The web app then loads that cache and silently refreshes the user token to
call Power BI ``executeQueries`` as a real user (bypassing the SP/MI 401
block on the tenant).

Usage (locally, once)::

    python bootstrap_pbi_token.py

Re-run when the cache file goes stale (~90 days inactive, or after password
change / CA policy revoke).

The cache file holds your refresh token — gitignore it and treat as secret.
"""

import json
import os
import sys
from pathlib import Path

import msal
import httpx

# ── Constants (match Web App env vars) ─────────────────────────────────────
CLIENT_ID = os.environ.get(
    "PBI_USER_CLIENT_ID", "e4c08c4a-a398-4955-af2f-0f63f892d049"
)
TENANT_ID = os.environ.get(
    "PBI_USER_TENANT_ID", "a85be8e2-4f70-43ec-a1fe-17302d408155"
)
WORKSPACE_ID = os.environ.get(
    "PBI_WORKSPACE_ID", "4435d932-4c62-46fd-ba3f-dd41a0d6d2f4"
)
DATASET_ID = os.environ.get(
    "PBI_DATASET_ID", "192c798b-0a94-4791-8520-0922452167aa"
)
SCOPES = ["https://analysis.windows.net/powerbi/api/.default"]
CACHE_PATH = Path(__file__).parent / ".pbi_cache.json"


def main() -> int:
    cache = msal.SerializableTokenCache()
    if CACHE_PATH.exists():
        cache.deserialize(CACHE_PATH.read_text(encoding="utf-8"))
        print(f"ℹ️  Loaded existing cache from {CACHE_PATH}")

    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        token_cache=cache,
    )

    # Try silent first (in case cache is still good)
    accounts = app.get_accounts()
    result = None
    if accounts:
        print(f"ℹ️  Trying silent refresh for {accounts[0].get('username')} ...")
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result or "access_token" not in result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            print("❌ Failed to initiate device flow:", json.dumps(flow, indent=2))
            return 2
        print()
        print("=" * 70)
        print(flow["message"])
        print("=" * 70)
        print()
        result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        print("❌ Token acquisition failed:")
        print(json.dumps(result, indent=2))
        return 3

    # Persist cache
    CACHE_PATH.write_text(cache.serialize(), encoding="utf-8")
    try:
        os.chmod(CACHE_PATH, 0o600)
    except Exception:
        pass  # Windows perms differ
    print(f"✅ Cache saved to {CACHE_PATH}")

    # Validate by hitting executeQueries
    print("🔎 Validating token against PBI executeQueries ...")
    url = (
        f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}"
        f"/datasets/{DATASET_ID}/executeQueries"
    )
    body = {
        "queries": [{"query": 'EVALUATE ROW("ping", 1)'}],
        "serializerSettings": {"includeNulls": True},
    }
    try:
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {result['access_token']}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=30.0,
        )
    except Exception as e:
        print(f"❌ HTTP call failed: {e}")
        return 4

    if resp.status_code == 200:
        print("✅ PBI executeQueries succeeded as your user. Bootstrap complete.")
        print(json.dumps(resp.json(), indent=2)[:400])
        return 0
    print(f"❌ PBI returned {resp.status_code}: {resp.text[:1000]}")
    print(
        "Token was acquired but PBI rejected it — check workspace/dataset access "
        "for your user."
    )
    return 5


if __name__ == "__main__":
    sys.exit(main())
