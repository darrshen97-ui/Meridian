"""Ledger endpoints. Thin: parse request, call service, shape response."""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.routers.deps import CurrentUser, DbSession
from app.services.dashboard import DashboardService
from app.services.ledger import LedgerError, LedgerService

router = APIRouter(prefix="/api", tags=["ledger"])


def register_exception_handler(app) -> None:
    @app.exception_handler(LedgerError)
    async def handle_ledger_error(request: Request, exc: LedgerError):
        return JSONResponse(status_code=exc.status_code,
                            content={"detail": exc.message})


@router.get("/dashboard")
async def dashboard(session: DbSession, user: CurrentUser):
    return await DashboardService(session).overview(user.id)


@router.get("/institutions")
async def list_institutions(session: DbSession, user: CurrentUser):
    return [asdict(x) for x in await LedgerService(session).list_institutions(user.id)]


@router.get("/accounts")
async def list_accounts(session: DbSession, user: CurrentUser):
    return [asdict(x) for x in await LedgerService(session).list_accounts(user.id)]


@router.get("/transactions")
async def list_transactions(
    session: DbSession,
    user: CurrentUser,
    account_id: int | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    q: str | None = None,
    category_id: int | None = None,
    source: str | None = None,
    uncategorized: bool = False,
    limit: int = 200,
    offset: int = 0,
):
    items = await LedgerService(session).list_transactions(
        user.id, account_id=account_id, date_from=date_from, date_to=date_to,
        q=q, category_id=category_id, source=source, uncategorized=uncategorized,
        limit=limit, offset=offset,
    )
    return [asdict(x) for x in items]


class CategoryUpdate(BaseModel):
    category_id: int


@router.patch("/transactions/{transaction_id}/category")
async def set_transaction_category(transaction_id: int, body: CategoryUpdate,
                                   session: DbSession, user: CurrentUser):
    updated = await LedgerService(session).set_transaction_category(
        user.id, transaction_id, body.category_id)
    return asdict(updated)


@router.get("/balances")
async def latest_balances(session: DbSession, user: CurrentUser):
    from app.repositories.sync import BalanceRepository

    latest = await BalanceRepository(session).latest_by_account(user.id)
    return list(latest.values())


@router.get("/categories")
async def list_categories(session: DbSession, user: CurrentUser):
    return [asdict(x) for x in await LedgerService(session).list_categories(user.id)]


@router.get("/documents")
async def list_documents(session: DbSession, user: CurrentUser):
    return [asdict(x) for x in await LedgerService(session).list_documents(user.id)]


@router.get("/budgets")
async def list_budgets(session: DbSession, user: CurrentUser):
    return [asdict(x) for x in await LedgerService(session).list_budgets(user.id)]
