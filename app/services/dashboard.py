"""Dashboard aggregation — answers "am I okay?" in one payload.

Spending power (brief §2) is liquid capital only: checking + savings +
payment-app balances, minus known upcoming obligations. Investments and crypto
are explicitly excluded. Obligations = current credit-card balances owed
(docs/DECISIONS.md D-016).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.analytics import AnalyticsRepository
from app.repositories.ledger import AccountRepository, TransactionRepository
from app.repositories.sync import BalanceRepository


def _month_bounds(day: dt.date) -> tuple[dt.date, dt.date]:
    first = day.replace(day=1)
    next_first = (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return first, next_first - dt.timedelta(days=1)


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.accounts = AccountRepository(session)
        self.balances = BalanceRepository(session)
        self.transactions = TransactionRepository(session)
        self.analytics = AnalyticsRepository(session)

    async def overview(self, user_id: int, today: dt.date | None = None) -> dict:
        today = today or dt.date.today()
        accounts = await self.accounts.list(user_id)
        latest = await self.balances.latest_by_account(user_id)

        liquid, cards = [], []
        liquid_total = 0
        obligations_total = 0
        for a in accounts:
            balance = latest.get(a.id)
            current = balance["current_minor"] if balance else None
            if a.is_liquid and a.closed_at is None:
                liquid.append({"account_id": a.id, "display_name": a.display_name,
                               "mask": a.mask, "current_minor": current,
                               "as_of": balance["as_of"] if balance else None})
                liquid_total += current or 0
            if a.type == "credit_card" and current is not None and current < 0:
                cards.append({"account_id": a.id, "display_name": a.display_name,
                              "mask": a.mask, "owed_minor": -current})
                obligations_total += -current

        this_start, this_end = _month_bounds(today)
        prev_start, prev_end = _month_bounds(this_start - dt.timedelta(days=1))
        this_month = await self.analytics.month_flow(user_id, this_start, this_end)
        prev_month = await self.analytics.month_flow(user_id, prev_start, prev_end)

        recent = await self.transactions.list(user_id, limit=10)
        review_count = await self.analytics.review_count(user_id)

        return {
            "as_of": today.isoformat(),
            "spending_power_minor": liquid_total - obligations_total,
            "liquid_minor": liquid_total,
            "obligations_minor": obligations_total,
            "liquid_accounts": liquid,
            "card_balances": cards,
            "this_month": {"label": today.strftime("%B %Y"), **this_month},
            "last_month": {"label": prev_start.strftime("%B %Y"), **prev_month},
            "needs_attention": {
                "review_count": review_count,
                "unresolved_findings": 0,   # reconciliation lands in milestone 10
            },
            "recent": [asdict(t) for t in recent],
        }
