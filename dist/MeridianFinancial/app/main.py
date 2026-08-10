"""Meridian Financial — application entry point."""
from __future__ import annotations

import logging
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import APP_VERSION, get_settings
from app.routers import ai as ai_router
from app.routers import auth as auth_router
from app.routers import budgets as budgets_router
from app.routers import coach as coach_router
from app.routers import documents as documents_router
from app.routers import ledger as ledger_router
from app.routers import reconciliation as reconciliation_router
from app.routers import sync as sync_router
from app.services.auth import AuthError

STATIC_DIR = Path(__file__).parent / "static"

log = logging.getLogger("meridian")

# Python's mimetypes reads the Windows registry, where .js is frequently mapped to
# text/plain by other software. Browsers apply strict MIME checking to ES modules,
# so a mis-typed bundle is silently refused and the page renders blank. Registering
# the correct types here overrides whatever the machine claims (D-025).
CONTENT_TYPES = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".html": "text/html",
}
for _suffix, _type in CONTENT_TYPES.items():
    mimetypes.add_type(_type, _suffix)


TEXTUAL = {".js", ".mjs", ".css", ".json", ".html", ".svg"}


def content_type_for(suffix: str) -> str | None:
    """Our own answer, independent of whatever the machine's MIME registry says."""
    declared = CONTENT_TYPES.get(suffix.lower())
    if declared is None:
        return None
    return f"{declared}; charset=utf-8" if suffix.lower() in TEXTUAL else declared


class TypedStaticFiles(StaticFiles):
    """StaticFiles that trusts our table instead of the host's MIME registry.

    Starlette re-guesses the content type on every request, so registering types
    at import time is not enough on a machine that mislabels JavaScript.
    """

    def file_response(self, full_path, stat_result, scope, status_code=200):
        response = super().file_response(full_path, stat_result, scope, status_code)
        declared = content_type_for(Path(full_path).suffix)
        if declared:
            response.headers["content-type"] = declared
        return response


def index_file_exists() -> bool:
    return (STATIC_DIR / "index.html").exists()

MISSING_UI_PAGE = """<!doctype html>
<meta charset="utf-8"><title>Meridian — interface not built</title>
<style>
 body{font:15px/1.5 system-ui,sans-serif;color:#16181D;background:#FBFBFA;
      margin:0;padding:64px 24px}
 main{max-width:620px;margin:0 auto}
 h1{font-size:24px;font-weight:600;margin:0 0 4px}
 p{color:#6E7178;margin:0 0 16px}
 code{font-family:ui-monospace,monospace;background:#fff;border:1px solid #E6E6E4;
      padding:2px 6px}
 hr{border:0;border-top:1px solid #E6E6E4;margin:24px 0}
</style>
<main>
 <h1>Meridian is running, but its interface isn't in this copy.</h1>
 <p>The server started correctly — the prebuilt web interface
 (<code>app/static</code>) is missing from these files.</p>
 <hr>
 <p><strong>The fix:</strong> download the packaged release instead of the source
 archive — open <code>dist/MeridianFinancial-v0.1.zip</code>, extract it, and run the
 launcher from there. It contains the built interface.</p>
 <p><strong>Or build it here</strong> if you have Node installed:
 <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code>, then restart
 the launcher.</p>
 <hr>
 <p>The API itself is live: <code>/health</code> responds, and your data is intact.</p>
</main>
"""


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    # Isolation check (brief §12): warn loudly if the AI endpoint isn't local.
    from app.providers.llm import endpoint_is_loopback

    if not endpoint_is_loopback(settings.ollama_base_url):
        log.warning(
            "OLLAMA_BASE_URL (%s) does not resolve to a loopback address - "
            "AI features will refuse to run.", settings.ollama_base_url)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Meridian Financial", version=APP_VERSION,
                  docs_url=None, redoc_url=None, lifespan=_lifespan)

    @app.exception_handler(AuthError)
    async def handle_auth_error(request: Request, exc: AuthError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        # Full detail to the server log; a stable, non-leaking message to the client.
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={
            "detail": "Something went wrong on the server. The details are in the "
                      "server log; the action was not completed."})

    @app.get("/health")
    async def health():
        return {
            "status": "ok", "app": "meridian", "version": APP_VERSION,
            "ui_built": index_file_exists(),
            # Diagnostic: a value other than text/javascript means this machine's
            # MIME registry would have blocked the interface (see CONTENT_TYPES).
            "js_content_type": mimetypes.guess_type("bundle.js")[0],
        }

    app.include_router(auth_router.router)
    app.include_router(ledger_router.router)
    app.include_router(documents_router.router)
    app.include_router(sync_router.router)
    app.include_router(ai_router.router)
    app.include_router(reconciliation_router.router)
    app.include_router(coach_router.router)
    app.include_router(budgets_router.router)
    documents_router.register_exception_handler(app)
    sync_router.register_exception_handler(app)
    ledger_router.register_exception_handler(app)
    ai_router.register_exception_handler(app)

    # Prebuilt frontend, when present. In development the Vite dev server proxies /api.
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        app.mount("/assets", TypedStaticFiles(directory=STATIC_DIR / "assets"),
                  name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str):
            if path.startswith("api/"):
                # An unknown API route is an error, never a page of HTML.
                return JSONResponse(status_code=404,
                                    content={"detail": "No such API endpoint."})
            candidate = (STATIC_DIR / path).resolve()
            if path and candidate.is_file() and candidate.is_relative_to(STATIC_DIR.resolve()):
                return FileResponse(candidate,
                                    media_type=content_type_for(candidate.suffix))
            return FileResponse(index_file, media_type="text/html; charset=utf-8")
    else:
        # The API is up but the interface wasn't built into this copy. Say so in
        # the browser with the fix, instead of a bare 404 (non-negotiable #6).
        @app.get("/{path:path}", include_in_schema=False)
        async def missing_ui(path: str):
            if path.startswith("api/"):
                return JSONResponse(status_code=404,
                                    content={"detail": "No such API endpoint."})
            return HTMLResponse(status_code=503, content=MISSING_UI_PAGE)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=get_settings().port)
