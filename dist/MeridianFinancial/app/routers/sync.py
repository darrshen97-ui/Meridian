"""Sync, live events (SSE), and the labeled dev simulation control."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.providers.financial import get_provider
from app.routers.deps import CurrentUser, DbSession
from app.services.events import get_event_bus, sse_format
from app.services.sync import SyncError, SyncService

router = APIRouter(prefix="/api", tags=["sync"])


def register_exception_handler(app) -> None:
    @app.exception_handler(SyncError)
    async def handle_sync_error(request: Request, exc: SyncError):
        return JSONResponse(status_code=502, content={"detail": exc.message})


@router.post("/sync")
async def sync_now(session: DbSession, user: CurrentUser):
    """Manual 'Sync now'. Blocks until done; progress streams over /api/events."""
    return await SyncService(session).sync(user.id, user.email)


@router.get("/sync/status")
async def sync_status(session: DbSession, user: CurrentUser):
    return await SyncService(session).status(user.id)


@router.get("/events")
async def events(request: Request, user: CurrentUser):
    """Server-Sent Events stream: sync progress and new-transaction pushes."""
    bus = get_event_bus()
    queue = bus.subscribe(user.id)

    async def stream():
        try:
            yield ": connected\n\n"
            while True:
                if await request.is_disconnected():
                    return
                try:
                    event_type, data = await asyncio.wait_for(queue.get(), timeout=15)
                    yield sse_format(event_type, data)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            bus.unsubscribe(user.id, queue)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


class SimulateRequest(BaseModel):
    count: int = Field(default=3, ge=1, le=5)


@router.post("/dev/simulate-transactions")
async def simulate_transactions(body: SimulateRequest, session: DbSession,
                                user: CurrentUser):
    """DEVELOPMENT TOOL (labeled as such in Settings): inject 1-5 plausible
    transactions into the mock provider, then sync so they land live via SSE."""
    injected = get_provider().inject_transactions(user.email.split("@")[0], body.count)
    if not injected:
        return JSONResponse(status_code=422, content={
            "detail": "This profile has no mock-provider feed to inject into. "
                      "Use a demo profile (jordan/priya) for the simulation."})
    summary = await SyncService(session).sync(user.id, user.email)
    return {"injected": len(injected), "sync": summary}
