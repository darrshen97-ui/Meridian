"""Aggregate queries for the dashboard. User-scoped on every method."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction


class AnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def month_flow(self, user_id: int, start: dt.date, end: dt.date) -> dict:
        """Spending and income for a period; transfers between own accounts and
        pending rows don't count as either."""
        row = (await self.session.execute(
            select(
                func.coalesce(func.sum(case(
                    (Transaction.amount_minor < 0, -Transaction.amount_minor),
                    else_=0)), 0),
                func.coalesce(func.sum(case(
                    (Transaction.amount_minor > 0, Transaction.amount_minor),
                    else_=0)), 0),
            ).where(
                Transaction.user_id == user_id,
                Transaction.posted_date >= start,
                Transaction.posted_date <= end,
                Transaction.pending.is_(False),
                Transaction.type != "transfer",
            )
        )).one()
        return {"spent_minor": int(row[0]), "income_minor": int(row[1])}

    async def review_count(self, user_id: int) -> int:
        return int(await self.session.scalar(
            select(func.count(Transaction.id)).where(
                Transaction.user_id == user_id,
                Transaction.pending.is_(False),
                Transaction.reviewed_at.is_(None),
                (Transaction.category_id.is_(None))
                | (Transaction.category_confidence < 0.8),
            )
        ) or 0)
