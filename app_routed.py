import os
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from chainlit.utils import mount_chainlit

logger = logging.getLogger(__name__)

try:
    from commercial_backend.api.routes.chat import router as commercial_router
    _commercial_router_loaded = True
except Exception as _e:
    logger.warning("Commercial backend not loaded: %s", _e)
    _commercial_router_loaded = False

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Commercial routes (registered BEFORE Chainlit catch-all) ──────────────────

if _commercial_router_loaded:
    app.include_router(commercial_router)


@app.get("/api/commercial/me")
async def commercial_me(request: Request) -> JSONResponse:
    """Return the signed-in user's UPN from Azure AD Easy Auth headers."""
    upn = (
        request.headers.get("x-ms-client-principal-name")
        or request.headers.get("x-user-upn")
        or os.environ.get("LOCAL_DEV_UPN", "")
    )
    return JSONResponse({"upn": upn})


_dist = os.path.join(os.path.dirname(__file__), "commercial-frontend", "dist")
if os.path.isdir(_dist):
    app.mount("/commercial", StaticFiles(directory=_dist, html=True), name="commercial")
else:
    logger.warning("commercial-frontend/dist not found — /commercial route disabled")


# ── Chainlit at / — LAST so SSO OAuth callback URL stays unchanged ─────────────
mount_chainlit(app=app, target="app.py", path="/")