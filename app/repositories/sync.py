"""Sync-run and balance repositories. User-scoped on every method."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, Balance, SyncRun
from app.models.base import utcnow


class SyncRunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def start(self, user_id: int, provider_key: str) -> int:
        run = SyncRun(user_id=user_id, provider_key=provider_key, status="running")
        self.session.add(run)
        await self.session.flush()
        return run.id

    async def finish(self, user_id: int, run_id: int, *, status: str,
                     cursor: str | None, records_ingested: int,
                     error: str | None = None) -> None:
        run = await self.session.scalar(
            select(SyncRun).where(SyncRun.user_id == user_id, SyncRun.id == run_id))
        if run is None:
            return
        run.status = status
        run.cursor = cursor
        run.records_ingested = records_ingested
        run.error = error
        run.finished_at = utcnow()

    async def last(self, user_id: int, provider_key: str) -> SyncRun | None:
        return await self.session.scalar(
            select(SyncRun)
            .where(SyncRun.user_id == user_id, SyncRun.provider_key == provider_key)
            .order_by(SyncRun.id.desc()).limit(1))

    async def last_cursor(self, user_id: int, provider_key: str) -> str | None:
        run = await self.session.scalar(
            select(SyncRun)
            .where(SyncRun.user_id == user_id,
                   SyncRun.provider_key == provider_key,
                   SyncRun.status.in_(("succeeded", "partial")))
            .order_by(SyncRun.id.desc()).limit(1))
        return run.cursor if run else None


class BalanceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(self, user_id: int, *, account_id: int, as_of: dt.datetime,
                     current_minor: int, available_minor: int | None,
                     source: str) -> None:
        owned = await self.session.scalar(
            select(Account.id).where(Account.user_id == user_id,
                                     Account.id == account_id))
        if owned is None:
            return
        self.session.add(Balance(account_id=account_id, as_of=as_of,
                                 current_minor=current_minor,
                                 available_minor=available_minor, source=source))

    async def latest_by_account(self, user_id: int) -> dict[int, dict]:
        rows = await self.session.execute(
            select(Balance)
            .join(Account, Balance.account_id == Account.id)
            .where(Account.user_id == user_id)
            .order_by(Balance.account_id, Balance.as_of, Balance.id)
        )
        latest: dict[int, dict] = {}
        for (b,) in rows:
            latest[b.account_id] = {
                "account_id": b.account_id,
                "as_of": b.as_of.isoformat(),
                "current_minor": b.current_minor,
                "available_minor": b.available_minor,
                "source": b.source,
            }
        return latest
