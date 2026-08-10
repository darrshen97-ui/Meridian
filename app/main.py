"""Meridian Financial — application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
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
        return {"status": "ok", "app": "meridian", "version": APP_VERSION}

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
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str):
            if path.startswith("api/"):
                # An unknown API route is an error, never a page of HTML.
                return JSONResponse(status_code=404,
                                    content={"detail": "No such API endpoint."})
            candidate = (STATIC_DIR / path).resolve()
            if path and candidate.is_file() and candidate.is_relative_to(STATIC_DIR.resolve()):
                return FileResponse(candidate)
            return FileResponse(index_file)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=get_settings().port)
