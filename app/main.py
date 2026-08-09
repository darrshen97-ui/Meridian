"""Meridian Financial — application entry point."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import APP_VERSION, get_settings
from app.routers import auth as auth_router
from app.routers import ledger as ledger_router
from app.services.auth import AuthError

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="Meridian Financial", version=APP_VERSION,
                  docs_url=None, redoc_url=None)

    @app.exception_handler(AuthError)
    async def handle_auth_error(request: Request, exc: AuthError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.get("/health")
    async def health():
        return {"status": "ok", "app": "meridian", "version": APP_VERSION}

    app.include_router(auth_router.router)
    app.include_router(ledger_router.router)

    # Prebuilt frontend, when present. In development the Vite dev server proxies /api.
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str):
            candidate = (STATIC_DIR / path).resolve()
            if path and candidate.is_file() and candidate.is_relative_to(STATIC_DIR.resolve()):
                return FileResponse(candidate)
            return FileResponse(index_file)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=get_settings().port)
