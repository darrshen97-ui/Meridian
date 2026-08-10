"""Budget simulator (brief §2, §12): "what if I cut dining by 30%?"

All projection math is deterministic Python over the user's real historical
spending distribution — complete months only, transfers excluded. The model's
only job is a short explanation and second-order effects; without it, the
deterministic summary stands alone.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction
from app.providers.llm import LLMError, LLMUnavailable
from app.repositories.audit import AuditRepository
from app.repositories.ledger import CategoryRepository
from app.services.ai import AIService
from app.services.dashboard import DashboardService
from app.services.ledger import LedgerError

DEFAULT_LOOKBACK = 6
DEFAULT_HORIZON = 6

EXPLAIN_SCHEMA = {
    "type": "object",
    "properties": {"explanation": {"type": "string"},
                   "watch_out_for": {"type": "string"}},
    "required": ["explanation", "watch_out_for"],
}
EXPLAIN_SYSTEM = (
    "You explain a budget simulation to its owner in two or three plain sentences, "
    "then name one realistic second-order effect to watch for (e.g. spending that "
    "shifts to another category). Use only the numbers provided — never invent "
    "any. Respond with JSON only."
)


def _money(minor: int) -> str:
    sign = "-" if minor < 0 else ""
    a = abs(minor)
    return f"{sign}${a // 100:,}.{a % 100:02d}"


def _month_label(d: dt.date) -> str:
    return d.strftime("%b %Y")


def _add_months(d: dt.date, n: int) -> dt.date:
    month = d.month - 1 + n
    return dt.date(d.year + month // 12, month % 12 + 1, 1)


class SimulationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.categories = CategoryRepository(session)
        self.audit = AuditRepository(session)
        self.ai = AIService(session)

    async def simulate(self, user_id: int, adjustments: list[dict],
                       months_ahead: int = DEFAULT_HORIZON,
                       lookback_months: int = DEFAULT_LOOKBACK,
                       today: dt.date | None = None) -> dict:
        if not adjustments:
            raise LedgerError("Give at least one adjustment to simulate.",
                              status_code=422)
        today = today or dt.date.today()
        months_ahead = max(1, min(months_ahead, 24))
        lookback_months = max(2, min(lookback_months, 12))

        categories = {c.id: c.name for c in await self.categories.list(user_id)}
        for adj in adjustments:
            if adj.get("category_id") not in categories:
                raise LedgerError("That category doesn't exist.", status_code=404)

        # -- Historical distribution over COMPLETE months only ----------------
        current_first = today.replace(day=1)
        window_start = _add_months(current_first, -lookback_months)
        rows = list(await self.session.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.pending.is_(False),
                Transaction.type != "transfer",
                Transaction.posted_date >= window_start,
                Transaction.posted_date < current_first)))

        by_month_category: dict[str, dict[int | None, int]] = defaultdict(
            lambda: defaultdict(int))
        income_by_month: dict[str, int] = defaultdict(int)
        for t in rows:
            key = t.posted_date.strftime("%Y-%m")
            if t.amount_minor < 0:
                by_month_category[key][t.category_id] += -t.amount_minor
            else:
                income_by_month[key] += t.amount_minor
        months = sorted(by_month_category.keys())
        if len(months) < 2:
            raise LedgerError(
                "There isn't enough history yet to project from — the simulator "
                "needs at least two complete months of transactions.",
                status_code=409)

        n = len(months)
        spend_mean_total = sum(sum(m.values())
                               for m in by_month_category.values()) // n
        income_mean = sum(income_by_month.values()) // n

        # -- Per-adjustment baselines from the real distribution --------------
        adjusted_details = []
        monthly_delta = 0
        for adj in adjustments:
            cat_id = adj["category_id"]
            pct = float(adj["percent_change"])
            series = [by_month_category[m].get(cat_id, 0) for m in months]
            mean = sum(series) // n
            if mean == 0:
                raise LedgerError(
                    f"No categorized spending history for "
                    f"{categories[cat_id]} in the last {n} complete months — "
                    "categorize some transactions first, then simulate.",
                    status_code=409)
            new_mean = round(mean * (1 + pct / 100))
            monthly_delta += mean - new_mean
            adjusted_details.append({
                "category_id": cat_id, "category": categories[cat_id],
                "percent_change": pct,
                "monthly_mean_minor": mean,
                "monthly_min_minor": min(series), "monthly_max_minor": max(series),
                "adjusted_mean_minor": new_mean,
                "monthly_delta_minor": mean - new_mean,
            })

        # -- Projection --------------------------------------------------------
        power_now = (await DashboardService(self.session).overview(
            user_id, today=today))["spending_power_minor"]
        baseline_net = income_mean - spend_mean_total
        projection = []
        for m in range(1, months_ahead + 1):
            label = _month_label(_add_months(current_first, m))
            baseline = power_now + m * baseline_net
            adjusted = baseline + m * monthly_delta
            projection.append({
                "month": label,
                "baseline_power_minor": baseline,
                "adjusted_power_minor": adjusted,
                "cumulative_delta_minor": m * monthly_delta,
            })

        summary = (
            f"Over the last {n} complete months you averaged "
            + "; ".join(f"{_money(a['monthly_mean_minor'])}/month on {a['category']}"
                        for a in adjusted_details)
            + f". The change frees {_money(monthly_delta)} a month — "
            f"{_money(monthly_delta * months_ahead)} over {months_ahead} months."
        ) if monthly_delta >= 0 else (
            f"The change adds {_money(-monthly_delta)} of spending a month — "
            f"{_money(-monthly_delta * months_ahead)} over {months_ahead} months."
        )

        result = {
            "lookback_complete_months": n,
            "months_ahead": months_ahead,
            "income_monthly_mean_minor": income_mean,
            "spending_monthly_mean_minor": spend_mean_total,
            "spending_power_now_minor": power_now,
            "adjustments": adjusted_details,
            "monthly_delta_minor": monthly_delta,
            "projection": projection,
            "summary": summary,
            "model_explanation": None,
            "watch_out_for": None,
        }
        await self._explain(user_id, result)
        await self.audit.append(user_id, event="simulation.run", detail={
            "adjustments": [{k: a[k] for k in ("category", "percent_change")}
                            for a in adjusted_details],
            "monthly_delta_minor": monthly_delta})
        await self.session.commit()
        return result

    async def _explain(self, user_id: int, result: dict) -> None:
        facts = (
            f"Adjustments: " + "; ".join(
                f"{a['category']} {a['percent_change']:+.0f}% "
                f"(historical mean {_money(a['monthly_mean_minor'])}/mo, range "
                f"{_money(a['monthly_min_minor'])}–{_money(a['monthly_max_minor'])})"
                for a in result["adjustments"])
            + f". Monthly income mean {_money(result['income_monthly_mean_minor'])}, "
              f"monthly spending mean {_money(result['spending_monthly_mean_minor'])}. "
              f"Change frees {_money(result['monthly_delta_minor'])}/month, which is "
              f"{_money(result['projection'][-1]['cumulative_delta_minor'])} in total "
              f"over {result['months_ahead']} months; spending power now "
              f"{_money(result['spending_power_now_minor'])}, projected "
              f"{_money(result['projection'][-1]['adjusted_power_minor'])} after "
              f"{result['months_ahead']} months. Do not compute any other figures."
        )
        try:
            response = await self.ai.call_json(
                user_id, feature="simulation", system=EXPLAIN_SYSTEM,
                user=facts, schema=EXPLAIN_SCHEMA)
            explanation = str(response.parsed.get("explanation", "")).strip()
            watch = str(response.parsed.get("watch_out_for", "")).strip()
            if explanation:
                result["model_explanation"] = explanation
            if watch:
                result["watch_out_for"] = watch
        except (LLMUnavailable, LLMError):
            pass  # the deterministic summary stands alone
