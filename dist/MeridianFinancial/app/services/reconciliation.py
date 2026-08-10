"""Reconciliation engine (brief §2, §7, §12).

Deterministic matching and arithmetic in Python; the model's only job is
turning each structured finding into one clear sentence — with deterministic
plain-language templates as the degraded path when the model is absent.

How findings arise in the collapsed-ledger design: statement import and
provider sync merge matching rows into one (D-011/D-012), so by the time the
engine runs, a row's identities tell the story —
  * statement identity only  → the provider feed never saw it
  * provider identity only   → no statement contains it
  * both, but dated 1-3 days apart → matched across a date shift (informational,
    pre-resolved — never a false positive, per D-003)
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, Transaction
from app.parsers import find_parser
from app.providers.llm import LLMError, LLMUnavailable
from app.repositories.audit import AuditRepository
from app.repositories.ledger import AccountRepository
from app.repositories.reconciliation import ReconciliationRepository
from app.repositories.sync import BalanceRepository
from app.services.ai import AIService
from app.services.dedupe import similarity
from app.services.ledger import LedgerError

DUPLICATE_WINDOW_DAYS = 3
MISMATCH_WINDOW_DAYS = 1
MISMATCH_SIMILARITY = 0.6

NARRATION_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {"index": {"type": "integer"}, "sentence": {"type": "string"}},
        "required": ["index", "sentence"],
    }}},
    "required": ["items"],
}
NARRATION_SYSTEM = (
    "You write one plain, calm sentence describing a bank reconciliation finding "
    "for the account owner. State what happened; no advice, no apologies, no "
    "exclamation marks. Respond with JSON only."
)


def _money(minor: int) -> str:
    sign = "-" if minor < 0 else ""
    a = abs(minor)
    return f"{sign}${a // 100:,}.{a % 100:02d}"


class ReconciliationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.accounts = AccountRepository(session)
        self.balances = BalanceRepository(session)
        self.runs = ReconciliationRepository(session)
        self.audit = AuditRepository(session)
        self.ai = AIService(session)

    # -- Public API --------------------------------------------------------

    async def periods(self, user_id: int) -> list[dict]:
        periods = await self.runs.reconcilable_periods(user_id)
        runs = await self.runs.list_runs(user_id)
        by_key = {(r.account_id, r.period_start, r.period_end): r for r in runs}
        for p in periods:
            run = by_key.get((p["account_id"], p["period_start"], p["period_end"]))
            p["period_start"] = p["period_start"].isoformat()
            p["period_end"] = p["period_end"].isoformat()
            p["last_run"] = self._run_dict(run) if run else None
        return periods

    async def run(self, user_id: int, account_id: int, period_start: dt.date,
                  period_end: dt.date) -> dict:
        account = await self.accounts.get(user_id, account_id)
        if account is None:
            raise LedgerError("That account doesn't exist.", status_code=404)
        statement_ending = await self._statement_ending(user_id, account_id,
                                                        period_start, period_end)
        if statement_ending is None:
            raise LedgerError(
                "No imported statement covers this account and period, so there is "
                "nothing to reconcile against. Import the statement first.",
                status_code=409)

        rows = list(await self.session.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.account_id == account_id,
                Transaction.posted_date >= period_start,
                Transaction.posted_date <= period_end,
            ).order_by(Transaction.posted_date, Transaction.id)))

        await self.runs.delete_runs_for_period(user_id, account_id,
                                               period_start, period_end)
        run = await self.runs.create_run(user_id, account_id=account_id,
                                         period_start=period_start,
                                         period_end=period_end)

        findings = self._detect(rows, period_end)
        await self._narrate(user_id, findings)
        actionable = 0
        for f in findings:
            await self.runs.add_finding(
                user_id, run_id=run.id, kind=f["kind"],
                transaction_id=f["transaction_id"],
                counterpart_id=f.get("counterpart_id"),
                delta_minor=f.get("delta_minor"), narrative=f["narrative"],
                resolved=f["resolved"])
            actionable += 0 if f["resolved"] else 1

        computed_ending = await self._computed_ending(user_id, account_id, period_end)
        run.statement_ending_minor = statement_ending
        run.computed_ending_minor = computed_ending
        balances_agree = computed_ending is None or computed_ending == statement_ending
        run.status = "clean" if actionable == 0 and balances_agree else "findings"

        await self.audit.append(user_id, event="reconciliation.run", detail={
            "account_id": account_id, "period_start": period_start.isoformat(),
            "findings": len(findings), "actionable": actionable,
            "status": run.status})
        await self.session.commit()
        return await self.detail(user_id, run.id)

    async def run_all(self, user_id: int) -> list[dict]:
        out = []
        for p in await self.runs.reconcilable_periods(user_id):
            out.append(await self.run(user_id, p["account_id"],
                                      p["period_start"], p["period_end"]))
        return out

    async def detail(self, user_id: int, run_id: int) -> dict:
        run = await self.runs.get_run(user_id, run_id)
        if run is None:
            raise LedgerError("That reconciliation doesn't exist.", status_code=404)
        findings = await self.runs.findings_for_run(user_id, run_id)
        txn_ids = {f.transaction_id for f in findings if f.transaction_id} | \
                  {f.counterpart_id for f in findings if f.counterpart_id}
        txns = {}
        if txn_ids:
            for t in await self.session.scalars(
                    select(Transaction).where(Transaction.user_id == user_id,
                                              Transaction.id.in_(txn_ids))):
                txns[t.id] = {"id": t.id, "posted_date": t.posted_date.isoformat(),
                              "description": t.description_raw,
                              "amount_minor": t.amount_minor}
        return {
            **self._run_dict(run),
            "findings": [{
                "id": f.id, "kind": f.kind, "narrative": f.narrative,
                "delta_minor": f.delta_minor,
                "resolved": f.resolved_at is not None,
                "transaction": txns.get(f.transaction_id),
                "counterpart": txns.get(f.counterpart_id),
            } for f in findings],
        }

    async def resolve(self, user_id: int, finding_id: int) -> None:
        if not await self.runs.resolve_finding(user_id, finding_id):
            raise LedgerError("That finding doesn't exist.", status_code=404)
        await self.audit.append(user_id, event="reconciliation.finding_resolved",
                                detail={"finding_id": finding_id})
        await self.session.commit()

    # -- Detection (pure arithmetic — never the model) ---------------------

    def _detect(self, rows: list[Transaction], period_end: dt.date) -> list[dict]:
        findings: list[dict] = []
        stmt_only = [t for t in rows if t.source_document_id is not None
                     and t.external_id is None and not t.pending]
        prov_only = [t for t in rows if t.external_id is not None
                     and t.source_document_id is None and not t.pending]
        pending = [t for t in rows if t.pending]
        both = [t for t in rows if t.external_id is not None
                and t.source_document_id is not None]

        # Amount mismatches: a statement row and a provider row that look like the
        # same purchase but disagree on the amount pair up into ONE finding.
        matched_mismatch: set[int] = set()
        for s in stmt_only:
            best = None
            for p in prov_only:
                if p.id in matched_mismatch or s.amount_minor == p.amount_minor:
                    continue
                if abs((s.posted_date - p.posted_date).days) > MISMATCH_WINDOW_DAYS:
                    continue
                if similarity(s.description_raw, p.description_raw) < MISMATCH_SIMILARITY:
                    continue
                best = p
                break
            if best is not None:
                matched_mismatch.update((s.id, best.id))
                findings.append({
                    "kind": "amount_mismatch", "transaction_id": s.id,
                    "counterpart_id": best.id,
                    "delta_minor": s.amount_minor - best.amount_minor,
                    "resolved": False,
                    "template": (f"{s.description_raw} shows "
                                 f"{_money(s.amount_minor)} on the statement but "
                                 f"{_money(best.amount_minor)} in the live feed."),
                })

        for t in stmt_only:
            if t.id in matched_mismatch:
                continue
            findings.append({
                "kind": "missing_in_provider", "transaction_id": t.id,
                "counterpart_id": None, "delta_minor": t.amount_minor,
                "resolved": False,
                "template": (f"{t.description_raw} ({_money(t.amount_minor)}, "
                             f"{t.posted_date:%b %d}) is on the statement but never "
                             "appeared in the live account feed."),
            })
        for t in prov_only:
            if t.id in matched_mismatch:
                continue
            findings.append({
                "kind": "missing_in_statement", "transaction_id": t.id,
                "counterpart_id": None, "delta_minor": t.amount_minor,
                "resolved": False,
                "template": (f"{t.description_raw} ({_money(t.amount_minor)}, "
                             f"{t.posted_date:%b %d}) is in the live feed but on "
                             "no statement."),
            })
        for t in pending:
            if t.posted_date <= period_end:
                findings.append({
                    "kind": "missing_in_statement", "transaction_id": t.id,
                    "counterpart_id": None, "delta_minor": t.amount_minor,
                    "resolved": False,
                    "template": (f"{t.description_raw} ({_money(t.amount_minor)}) has "
                                 f"been pending since {t.posted_date:%b %d} and never "
                                 "cleared onto a statement."),
                })

        # Duplicate suspects: same amount + same normalized description within
        # three days, among fully-settled rows.
        settled = sorted((t for t in rows if not t.pending),
                         key=lambda t: (t.amount_minor, t.description_raw,
                                        t.posted_date))
        for a, b in zip(settled, settled[1:]):
            if a.amount_minor == b.amount_minor and a.amount_minor < 0 \
                    and a.description_raw == b.description_raw \
                    and 0 < (b.posted_date - a.posted_date).days <= DUPLICATE_WINDOW_DAYS:
                findings.append({
                    "kind": "duplicate_suspected", "transaction_id": a.id,
                    "counterpart_id": b.id, "delta_minor": a.amount_minor,
                    "resolved": False,
                    "template": (f"{a.description_raw} was charged twice — "
                                 f"{_money(a.amount_minor)} on {a.posted_date:%b %d} "
                                 f"and again on {b.posted_date:%b %d}."),
                })

        # Date shifts: matched silently across sources; informational only.
        for t in both:
            if t.transaction_date is None:
                continue
            shift = abs((t.transaction_date - t.posted_date).days)
            if 1 <= shift <= 3:
                findings.append({
                    "kind": "date_shift", "transaction_id": t.id,
                    "counterpart_id": None, "delta_minor": None,
                    "resolved": True,   # matched, not flagged (D-003)
                    "template": (f"{t.description_raw} posted {shift} day"
                                 f"{'s' if shift > 1 else ''} apart on the statement "
                                 "and the live feed — matched automatically."),
                })
        return findings

    # -- Narration (the model's ONLY job here) -----------------------------

    async def _narrate(self, user_id: int, findings: list[dict]) -> None:
        for f in findings:
            f["narrative"] = f["template"]
        unresolved = [f for f in findings if not f["resolved"]][:20]
        if not unresolved:
            return
        lines = [f"{i}. kind={f['kind']} :: {f['template']}"
                 for i, f in enumerate(unresolved)]
        try:
            result = await self.ai.call_json(
                user_id, feature="reconciliation",
                system=NARRATION_SYSTEM,
                user="Rewrite each finding as one clear sentence:\n" + "\n".join(lines),
                schema=NARRATION_SCHEMA)
            for item in result.parsed.get("items", []):
                try:
                    sentence = str(item["sentence"]).strip()
                    if sentence:
                        unresolved[int(item["index"])]["narrative"] = sentence
                except (KeyError, ValueError, IndexError, TypeError):
                    continue
        except (LLMUnavailable, LLMError):
            pass  # deterministic templates stand on their own

    # -- Balances ----------------------------------------------------------

    async def _statement_ending(self, user_id: int, account_id: int,
                                period_start: dt.date,
                                period_end: dt.date) -> int | None:
        docs = list(await self.session.scalars(
            select(Document).where(
                Document.user_id == user_id,
                Document.account_id == account_id,
                Document.period_start == period_start,
                Document.period_end == period_end,
                Document.parse_status.in_(("parsed", "partial")))))
        for doc in docs:
            path = Path(doc.stored_path)
            if not path.exists():
                continue
            content = path.read_bytes()
            parser = find_parser(doc.filename, content)
            if parser is None:
                continue
            parsed = parser.parse(doc.filename, content)
            if parsed.closing_balance_minor is not None:
                return parsed.closing_balance_minor
        return None

    async def _computed_ending(self, user_id: int, account_id: int,
                               period_end: dt.date) -> int | None:
        """Anchor on the latest provider balance and walk back through the ledger."""
        latest = await self.balances.latest_by_account(user_id)
        anchor = latest.get(account_id)
        if anchor is None:
            return None
        after_sum = await self.session.scalar(
            select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
                Transaction.user_id == user_id,
                Transaction.account_id == account_id,
                Transaction.pending.is_(False),
                Transaction.posted_date > period_end))
        return int(anchor["current_minor"]) - int(after_sum or 0)

    @staticmethod
    def _run_dict(run) -> dict:
        delta = None
        if run.statement_ending_minor is not None \
                and run.computed_ending_minor is not None:
            delta = run.computed_ending_minor - run.statement_ending_minor
        return {
            "run_id": run.id, "account_id": run.account_id,
            "period_start": run.period_start.isoformat(),
            "period_end": run.period_end.isoformat(),
            "statement_ending_minor": run.statement_ending_minor,
            "computed_ending_minor": run.computed_ending_minor,
            "delta_minor": delta,
            "status": run.status,
            "run_at": run.run_at.isoformat() if run.run_at else None,
        }
