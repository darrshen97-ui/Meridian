"""Reconciliation endpoints. Thin over ReconciliationService."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter
from pydantic import BaseModel

from app.routers.deps import CurrentUser, DbSession
from app.services.reconciliation import ReconciliationService

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])


@router.get("/periods")
async def periods(session: DbSession, user: CurrentUser):
    return await ReconciliationService(session).periods(user.id)


class RunRequest(BaseModel):
    account_id: int
    period_start: dt.date
    period_end: dt.date


@router.post("/run")
async def run(body: RunRequest, session: DbSession, user: CurrentUser):
    return await ReconciliationService(session).run(
        user.id, body.account_id, body.period_start, body.period_end)


@router.post("/run-all")
async def run_all(session: DbSession, user: CurrentUser):
    return await ReconciliationService(session).run_all(user.id)


@router.get("/{run_id}")
async def detail(run_id: int, session: DbSession, user: CurrentUser):
    return await ReconciliationService(session).detail(user.id, run_id)


@router.post("/findings/{finding_id}/resolve", status_code=204)
async def resolve(finding_id: int, session: DbSession, user: CurrentUser):
    await ReconciliationService(session).resolve(user.id, finding_id)
