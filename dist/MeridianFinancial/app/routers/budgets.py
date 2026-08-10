"""Budget targets and the what-if simulator. Thin over the services."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.routers.deps import CurrentUser, DbSession
from app.services.budgets import BudgetService
from app.services.simulation import SimulationService

router = APIRouter(prefix="/api", tags=["budgets"])


@router.get("/budgets/overview")
async def overview(session: DbSession, user: CurrentUser, period: str | None = None):
    period = period or dt.date.today().strftime("%Y-%m")
    return await BudgetService(session).overview(user.id, period)


class TargetRequest(BaseModel):
    target_minor: int
    period: str | None = None


@router.put("/budgets/{category_id}")
async def set_target(category_id: int, body: TargetRequest,
                     session: DbSession, user: CurrentUser):
    period = body.period or dt.date.today().strftime("%Y-%m")
    return await BudgetService(session).set_target(
        user.id, category_id, body.target_minor, period)


@router.delete("/budgets/{category_id}", status_code=204)
async def clear_target(category_id: int, session: DbSession, user: CurrentUser):
    await BudgetService(session).clear_target(user.id, category_id)


class Adjustment(BaseModel):
    category_id: int
    percent_change: float = Field(ge=-100, le=200)


class SimulateRequest(BaseModel):
    adjustments: list[Adjustment] = Field(min_length=1, max_length=5)
    months_ahead: int = Field(default=6, ge=1, le=24)
    lookback_months: int = Field(default=6, ge=2, le=12)


@router.post("/simulate")
async def simulate(body: SimulateRequest, session: DbSession, user: CurrentUser):
    return await SimulationService(session).simulate(
        user.id, [a.model_dump() for a in body.adjustments],
        months_ahead=body.months_ahead, lookback_months=body.lookback_months)
