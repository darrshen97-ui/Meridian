"""Budgets: monthly targets by category, actuals from the real ledger."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction
from app.repositories.audit import AuditRepository
from app.repositories.ledger import BudgetRepository, CategoryRepository
from app.services.ledger import LedgerError


def month_bounds(period: str) -> tuple[dt.date, dt.date]:
    try:
        year, month = int(period[:4]), int(period[5:7])
        first = dt.date(year, month, 1)
    except (ValueError, IndexError):
        raise LedgerError("Period must look like 2026-08.", status_code=422)
    next_first = (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return first, next_first - dt.timedelta(days=1)


class BudgetService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.budgets = BudgetRepository(session)
        self.categories = CategoryRepository(session)
        self.audit = AuditRepository(session)

    async def overview(self, user_id: int, period: str) -> dict:
        first, last = month_bounds(period)
        categories = await self.categories.list(user_id)
        budgets = {b.category_id: b for b in await self.budgets.list(user_id)}

        spent: dict[int | None, int] = defaultdict(int)
        rows = await self.session.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.pending.is_(False),
                Transaction.type != "transfer",
                Transaction.amount_minor < 0,
                Transaction.posted_date >= first,
                Transaction.posted_date <= last))
        for t in rows:
            spent[t.category_id] += -t.amount_minor

        entries = []
        for c in sorted(categories, key=lambda c: c.name):
            budget = budgets.get(c.id)
            actual = spent.get(c.id, 0)
            if budget is None and actual == 0:
                continue  # nothing to say about this category this month
            entries.append({
                "category_id": c.id, "category": c.name,
                "target_minor": budget.target_minor if budget else None,
                "actual_minor": actual,
                "over_minor": (actual - budget.target_minor)
                if budget and actual > budget.target_minor else 0,
            })
        return {
            "period": period,
            "entries": entries,
            "uncategorized_minor": spent.get(None, 0),
            "totals": {
                "target_minor": sum(e["target_minor"] or 0 for e in entries),
                "actual_minor": sum(e["actual_minor"] for e in entries)
                + spent.get(None, 0),
            },
        }

    async def set_target(self, user_id: int, category_id: int,
                         target_minor: int, period: str) -> dict:
        if target_minor < 0:
            raise LedgerError("A budget target can't be negative.", status_code=422)
        category = await self.categories.get_visible(user_id, category_id)
        if category is None:
            raise LedgerError("That category doesn't exist.", status_code=404)
        first, _ = month_bounds(period)
        budget = await self.budgets.upsert_monthly(
            user_id, category_id=category_id, target_minor=target_minor,
            period_start=first)
        await self.audit.append(user_id, event="budget.set", detail={
            "category_id": category_id, "target_minor": target_minor})
        await self.session.commit()
        return {"category_id": budget.category_id,
                "target_minor": budget.target_minor}

    async def clear_target(self, user_id: int, category_id: int) -> None:
        removed = await self.budgets.delete_monthly(user_id, category_id)
        if not removed:
            raise LedgerError("No budget target exists for that category.",
                              status_code=404)
        await self.audit.append(user_id, event="budget.cleared",
                                detail={"category_id": category_id})
        await self.session.commit()
