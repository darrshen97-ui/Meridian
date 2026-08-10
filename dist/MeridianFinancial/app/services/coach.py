"""AI Spending Coach (brief §12): conversational, grounded, honest.

The model must query before answering — every answer carries the tool calls it
made and the transactions it looked at, so the user can verify the reasoning.
The tool loop is capped at 4 calls; if the model can't resolve within that, it
says what it found and what it couldn't determine.

Tool use is schema-driven: each step the model emits a JSON decision (call a
tool with arguments, or answer). This is deliberate — it is dramatically more
reliable on small local models than native function-calling, and it works
identically across LLM providers. Tools are scoped to the authenticated user at
the execution layer; the model never receives (and cannot inject) a user id.
"""
from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction
from app.providers.llm import LLMError, LLMUnavailable
from app.repositories.audit import AuditRepository
from app.repositories.ledger import (
    AccountRepository,
    BudgetRepository,
    CategoryRepository,
    UserCorrectionRepository,
)
from app.repositories.sync import BalanceRepository
from app.services.ai import AIService

MAX_TOOL_CALLS = 4
MAX_ROWS = 20
MAX_HISTORY = 6

STEP_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["call_tool", "answer"]},
        "tool": {"type": "string"},
        "arguments": {"type": "object"},
        "answer": {"type": "string"},
    },
    "required": ["action"],
}

SYSTEM_PROMPT = (
    "You are Meridian's spending coach. You answer questions about the user's own "
    "finances using ONLY data returned by tools — never from memory or guesswork. "
    "Rules:\n"
    "- Always call at least one tool before answering.\n"
    "- Amounts in tool results are integer cents; negative means money out.\n"
    "- Be direct. If the data supports 'you can't comfortably afford this', say "
    "exactly that. If the data is insufficient, say what's missing.\n"
    "- Copy dollar figures character-for-character from tool results (tools "
    "already compute totals) — never do arithmetic yourself.\n"
    "- Answer in a few plain sentences with real numbers. No advice-column filler.\n"
    "Each turn respond with JSON: either "
    '{"action":"call_tool","tool":"<name>","arguments":{...}} or '
    '{"action":"answer","answer":"..."}.'
)


def _money(minor: int) -> str:
    sign = "-" if minor < 0 else ""
    a = abs(minor)
    return f"{sign}${a // 100:,}.{a % 100:02d}"


class CoachService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.accounts = AccountRepository(session)
        self.balances = BalanceRepository(session)
        self.categories = CategoryRepository(session)
        self.corrections = UserCorrectionRepository(session)
        self.budgets = BudgetRepository(session)
        self.audit = AuditRepository(session)
        self.ai = AIService(session)
        self._seen_txn_ids: list[int] = []

    # -- Tool registry -----------------------------------------------------
    # Every executor takes user_id at the execution layer (brief §12).

    def _tools(self) -> dict:
        return {
            "query_transactions": {
                "description": ("List transactions. Args: date_from, date_to "
                                "(YYYY-MM-DD), merchant (substring), category, "
                                "min_amount/max_amount (dollars, absolute), "
                                "limit (max 20)."),
                "run": self._t_query_transactions,
            },
            "get_account_balances": {
                "description": ("Current balances. Args: include_non_liquid "
                                "(bool; false = spending-power accounts only)."),
                "run": self._t_balances,
            },
            "get_budget_targets": {
                "description": "Budget targets. Args: period (YYYY-MM).",
                "run": self._t_budgets,
            },
            "fetch_category_history": {
                "description": ("How this user has filed a merchant before. "
                                "Args: merchant (substring)."),
                "run": self._t_category_history,
            },
            "get_spending_summary": {
                "description": ("Totals of spending. Args: group_by "
                                "('category'|'month'|'merchant'), date_from, "
                                "date_to (YYYY-MM-DD)."),
                "run": self._t_spending_summary,
            },
        }

    async def _t_query_transactions(self, user_id: int, args: dict) -> dict:
        rows, note = await self._query_rows(user_id, args)
        if not rows and args.get("merchant") and args.get("category"):
            # A merchant search shouldn't die on the category filter (rows may be
            # uncategorized) — deterministically widen and say so.
            rows, _ = await self._query_rows(user_id,
                                             {**args, "category": None})
            if rows:
                note = ("The category filter matched nothing (those rows may be "
                        "uncategorized), so it was ignored for this result.")
        self._seen_txn_ids.extend(r.id for r in rows)
        total = sum(r.amount_minor for r in rows)
        out = {
            "count": len(rows),
            "TOTAL_OF_ALL_LISTED_TRANSACTIONS":
                f"{_money(total)} <- use this figure when asked for a total",
            "transactions": [
                {"date": r.posted_date.isoformat(),
                 "description": r.description_raw[:60],
                 "amount": _money(r.amount_minor)} for r in rows],
        }
        if note:
            out["note"] = note
        return out

    async def _query_rows(self, user_id: int, args: dict):
        date_from = _parse_date(args.get("date_from")) or dt.date(2000, 1, 1)
        date_to = _parse_date(args.get("date_to")) or dt.date(2100, 1, 1)
        limit = min(int(args.get("limit", MAX_ROWS) or MAX_ROWS), MAX_ROWS)
        stmt = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.pending.is_(False),
            Transaction.posted_date >= date_from,
            Transaction.posted_date <= date_to)
        if args.get("merchant"):
            needle = f"%{args['merchant']}%"
            stmt = stmt.where(Transaction.description_raw.ilike(needle)
                              | Transaction.merchant.ilike(needle))
        if args.get("category"):
            ids = [c.id for c in await self.categories.list(user_id)
                   if c.name.lower() == str(args["category"]).lower()]
            stmt = stmt.where(Transaction.category_id.in_(ids or [-1]))
        if args.get("min_amount") is not None:
            stmt = stmt.where(Transaction.amount_minor
                              <= -int(float(args["min_amount"]) * 100))
        if args.get("max_amount") is not None:
            stmt = stmt.where(Transaction.amount_minor
                              >= -int(float(args["max_amount"]) * 100))
        rows = list(await self.session.scalars(
            stmt.order_by(Transaction.posted_date.desc()).limit(limit)))
        return rows, None

    async def _t_balances(self, user_id: int, args: dict) -> dict:
        include_all = bool(args.get("include_non_liquid", False))
        accounts = await self.accounts.list(user_id)
        latest = await self.balances.latest_by_account(user_id)
        out = []
        for a in accounts:
            if a.closed_at is not None:
                continue
            if not include_all and not a.is_liquid:
                continue
            b = latest.get(a.id)
            out.append({"account": f"{a.display_name}"
                                   f"{' ..' + a.mask if a.mask else ''}",
                        "type": a.type,
                        "balance": _money(b["current_minor"]) if b else "unknown"})
        return {"accounts": out}

    async def _t_budgets(self, user_id: int, args: dict) -> dict:
        rows = await self.budgets.list(user_id)
        if not rows:
            return {"budgets": [], "note": "No budget targets are set yet."}
        categories = {c.id: c.name for c in await self.categories.list(user_id)}
        return {"budgets": [
            {"category": categories.get(b.category_id, "?"),
             "period_start": b.period_start.isoformat(),
             "target": _money(b.target_minor)} for b in rows[:MAX_ROWS]]}

    async def _t_category_history(self, user_id: int, args: dict) -> dict:
        needle = str(args.get("merchant", "")).upper()
        corrections = await self.corrections.list(user_id)
        categories = {c.id: c.name for c in await self.categories.list(user_id)}
        matches = [{"pattern": c.merchant_pattern,
                    "category": categories.get(c.category_id, "?")}
                   for c in corrections if needle and needle in c.merchant_pattern]
        return {"corrections": matches[:10],
                "note": None if matches else
                "The user hasn't filed this merchant before."}

    async def _t_spending_summary(self, user_id: int, args: dict) -> dict:
        date_from = _parse_date(args.get("date_from")) or dt.date(2000, 1, 1)
        date_to = _parse_date(args.get("date_to")) or dt.date(2100, 1, 1)
        group_by = str(args.get("group_by", "category"))
        rows = list(await self.session.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.pending.is_(False),
                Transaction.type != "transfer",
                Transaction.amount_minor < 0,
                Transaction.posted_date >= date_from,
                Transaction.posted_date <= date_to)))
        categories = {c.id: c.name for c in await self.categories.list(user_id)}
        buckets: dict[str, int] = defaultdict(int)
        for r in rows:
            if group_by == "month":
                key = r.posted_date.strftime("%Y-%m")
            elif group_by == "merchant":
                key = (r.merchant or r.description_raw)[:40]
            else:
                key = categories.get(r.category_id, "Uncategorized")
            buckets[key] += -r.amount_minor
        top = sorted(buckets.items(), key=lambda kv: -kv[1])[:MAX_ROWS]
        return {"group_by": group_by,
                "total_spent": _money(sum(buckets.values())),
                "groups": [{"group": k, "spent": _money(v)} for k, v in top]}

    # -- The loop ----------------------------------------------------------

    async def ask(self, user_id: int, question: str,
                  history: list[dict] | None = None) -> dict:
        tools = self._tools()
        context = await self._context(user_id)
        transcript = [f"Context:\n{context}"]
        for h in (history or [])[-MAX_HISTORY:]:
            role = "User" if h.get("role") == "user" else "Coach"
            transcript.append(f"{role}: {str(h.get('content', ''))[:400]}")
        transcript.append(f"User question: {question.strip()[:500]}")

        tool_list = "\n".join(f"- {name}: {t['description']}"
                              for name, t in tools.items())
        calls_made: list[dict] = []
        answer: str | None = None

        try:
            for step in range(MAX_TOOL_CALLS + 1):
                must_answer = step == MAX_TOOL_CALLS
                prompt = "\n\n".join(transcript) + "\n\nAvailable tools:\n" + tool_list
                if must_answer:
                    prompt += ("\n\nYou have used all tool calls. Answer NOW with "
                               "what you found and what you couldn't determine.")
                result = await self.ai.call_json(
                    user_id, feature="coach", system=SYSTEM_PROMPT, user=prompt,
                    schema=STEP_SCHEMA)
                decision = result.parsed
                if decision.get("action") == "answer" or must_answer:
                    answer = str(decision.get("answer") or "").strip()
                    break
                name = str(decision.get("tool") or "")
                args = decision.get("arguments") or {}
                if name not in tools:
                    transcript.append(
                        f"Tool error: '{name}' does not exist. Choose from the list.")
                    continue
                signature = f"{name}:{json.dumps(args, sort_keys=True)}"
                if any(c["_signature"] == signature for c in calls_made):
                    transcript.append(
                        "You already made that exact call — its result is above. "
                        "Change the arguments or answer now.")
                    continue
                tool_result = await tools[name]["run"](user_id, args)
                payload = json.dumps(tool_result)[:4000]  # sane size for a small model
                computed_total = tool_result.get(
                    "TOTAL_OF_ALL_LISTED_TRANSACTIONS",
                    tool_result.get("total_spent"))
                calls_made.append({"tool": name, "arguments": args,
                                   "result_preview": payload[:200],
                                   "computed_total": (str(computed_total).split(" <-")[0]
                                                      if computed_total else None),
                                   "count": tool_result.get("count"),
                                   "_signature": signature})
                transcript.append(f"Tool {name}({json.dumps(args)[:200]}) returned:\n"
                                  f"{payload}")
        except (LLMUnavailable, LLMError) as exc:
            await self.session.commit()  # keep any ai_calls rows already logged
            return {"available": False, "message": exc.message,
                    "answer": None, "tool_calls": [], "transactions": []}

        if not answer:
            answer = ("I couldn't produce an answer from the data I retrieved. "
                      "Try asking a narrower question.")
        if not calls_made:
            answer = ("I couldn't verify this against your data (no query was made), "
                      "so I won't guess. Try rephrasing the question.")

        seen = []
        if self._seen_txn_ids:
            unique_ids = list(dict.fromkeys(self._seen_txn_ids))[:40]
            for t in await self.session.scalars(
                    select(Transaction).where(Transaction.user_id == user_id,
                                              Transaction.id.in_(unique_ids))):
                seen.append({"id": t.id, "posted_date": t.posted_date.isoformat(),
                             "description": t.description_raw,
                             "amount_minor": t.amount_minor})
        await self.audit.append(user_id, event="coach.asked", detail={
            "question": question[:120], "tool_calls": len(calls_made)})
        await self.session.commit()
        for c in calls_made:
            c.pop("_signature", None)
        return {"available": True, "message": None, "answer": answer,
                "tool_calls": calls_made,
                "transactions": sorted(seen, key=lambda r: r["posted_date"],
                                       reverse=True)}

    async def _context(self, user_id: int) -> str:
        """Tier 2 for the coach: taxonomy + accounts + the user's filing habits."""
        categories = ", ".join(sorted(c.name for c in
                                      await self.categories.list(user_id)))
        accounts = await self.accounts.list(user_id)
        account_lines = "; ".join(
            f"{a.display_name}{' ..' + a.mask if a.mask else ''} ({a.type}"
            f"{', closed' if a.closed_at else ''})" for a in accounts) or "none"
        corrections = await self.corrections.list(user_id)
        categories_by_id = {c.id: c.name for c in await self.categories.list(user_id)}
        habit_lines = "\n".join(
            f'- files "{c.merchant_pattern}" under '
            f"{categories_by_id.get(c.category_id, '?')}"
            for c in corrections[:8])
        today = dt.date.today().isoformat()
        out = (f"Today is {today}. Categories: {categories}.\n"
               f"Accounts: {account_lines}.")
        if habit_lines:
            out += f"\nThis user's filing habits:\n{habit_lines}"
        return out


def _parse_date(value) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
