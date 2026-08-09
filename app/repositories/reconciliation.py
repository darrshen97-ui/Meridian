"""Reconciliation repositories. Findings are scoped through their run's user."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, Reconciliation, ReconciliationFinding
from app.models.base import utcnow


class ReconciliationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_run(self, user_id: int, *, account_id: int,
                         period_start: dt.date, period_end: dt.date) -> Reconciliation:
        run = Reconciliation(user_id=user_id, account_id=account_id,
                             period_start=period_start, period_end=period_end,
                             status="running")
        self.session.add(run)
        await self.session.flush()
        return run

    async def add_finding(self, user_id: int, *, run_id: int, kind: str,
                          transaction_id: int | None, counterpart_id: int | None,
                          delta_minor: int | None, narrative: str,
                          resolved: bool = False) -> ReconciliationFinding:
        run = await self.get_run(user_id, run_id)
        if run is None:
            raise ValueError("run does not belong to user")
        finding = ReconciliationFinding(
            reconciliation_id=run_id, kind=kind, transaction_id=transaction_id,
            counterpart_id=counterpart_id, delta_minor=delta_minor,
            narrative=narrative, resolved_at=utcnow() if resolved else None)
        self.session.add(finding)
        await self.session.flush()
        return finding

    async def get_run(self, user_id: int, run_id: int) -> Reconciliation | None:
        return await self.session.scalar(
            select(Reconciliation).where(Reconciliation.user_id == user_id,
                                         Reconciliation.id == run_id))

    async def list_runs(self, user_id: int,
                        account_id: int | None = None) -> list[Reconciliation]:
        stmt = select(Reconciliation).where(Reconciliation.user_id == user_id)
        if account_id is not None:
            stmt = stmt.where(Reconciliation.account_id == account_id)
        return list(await self.session.scalars(
            stmt.order_by(Reconciliation.period_start.desc(),
                          Reconciliation.id.desc())))

    async def findings_for_run(self, user_id: int,
                               run_id: int) -> list[ReconciliationFinding]:
        run = await self.get_run(user_id, run_id)
        if run is None:
            return []
        return list(await self.session.scalars(
            select(ReconciliationFinding)
            .where(ReconciliationFinding.reconciliation_id == run_id)
            .order_by(ReconciliationFinding.id)))

    async def all_findings(self, user_id: int) -> list[ReconciliationFinding]:
        return list(await self.session.scalars(
            select(ReconciliationFinding)
            .join(Reconciliation,
                  ReconciliationFinding.reconciliation_id == Reconciliation.id)
            .where(Reconciliation.user_id == user_id)))

    async def resolve_finding(self, user_id: int, finding_id: int) -> bool:
        finding = await self.session.scalar(
            select(ReconciliationFinding)
            .join(Reconciliation,
                  ReconciliationFinding.reconciliation_id == Reconciliation.id)
            .where(Reconciliation.user_id == user_id,
                   ReconciliationFinding.id == finding_id))
        if finding is None:
            return False
        if finding.resolved_at is None:
            finding.resolved_at = utcnow()
        return True

    async def unresolved_count(self, user_id: int) -> int:
        return int(await self.session.scalar(
            select(func.count(ReconciliationFinding.id))
            .join(Reconciliation,
                  ReconciliationFinding.reconciliation_id == Reconciliation.id)
            .where(Reconciliation.user_id == user_id,
                   ReconciliationFinding.resolved_at.is_(None))) or 0)

    async def delete_runs_for_period(self, user_id: int, account_id: int,
                                     period_start: dt.date,
                                     period_end: dt.date) -> None:
        """Re-running a period replaces its previous run (and findings)."""
        runs = list(await self.session.scalars(
            select(Reconciliation).where(
                Reconciliation.user_id == user_id,
                Reconciliation.account_id == account_id,
                Reconciliation.period_start == period_start,
                Reconciliation.period_end == period_end)))
        for run in runs:
            for finding in await self.findings_for_run(user_id, run.id):
                await self.session.delete(finding)
            await self.session.delete(run)
        await self.session.flush()

    async def reconcilable_periods(self, user_id: int) -> list[dict]:
        """Every (account, period) an imported, period-bearing document covers."""
        rows = await self.session.execute(
            select(Document.account_id, Document.period_start, Document.period_end,
                   func.count(Document.id))
            .where(Document.user_id == user_id,
                   Document.account_id.is_not(None),
                   Document.period_start.is_not(None),
                   Document.period_end.is_not(None),
                   Document.parse_status.in_(("parsed", "partial")))
            .group_by(Document.account_id, Document.period_start, Document.period_end)
            .order_by(Document.period_start.desc()))
        return [{"account_id": r[0], "period_start": r[1], "period_end": r[2],
                 "documents": int(r[3])} for r in rows]
