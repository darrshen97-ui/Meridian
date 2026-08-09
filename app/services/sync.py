"""Sync service: pulls the provider's accounts, balances, and transaction stream
into the user's ledger with real incremental cursors, retry/backoff, and SSE
progress events. Runs are recorded in sync_runs (brief §11).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.financial import (
    AccountDTO,
    ProviderRateLimited,
    ProviderTransientError,
    TransactionDTO,
    get_provider,
)
from app.repositories.audit import AuditRepository
from app.repositories.ledger import (
    AccountRepository,
    InstitutionRepository,
    TransactionRepository,
)
from app.repositories.sync import BalanceRepository, SyncRunRepository
from app.services.dedupe import Existing, Incoming, dedupe_hash, match_incoming
from app.services.events import get_event_bus

MAX_ATTEMPTS = 5


class SyncError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


async def _with_retry(operation, describe: str):
    """Retry transient failures with exponential backoff; honor 429 delays."""
    delay = 0.2
    last: Exception | None = None
    for _attempt in range(MAX_ATTEMPTS):
        try:
            return await operation()
        except ProviderRateLimited as exc:
            last = exc
            await asyncio.sleep(exc.retry_after)
        except ProviderTransientError as exc:
            last = exc
            await asyncio.sleep(delay)
            delay *= 2
    raise SyncError(f"{describe} kept failing after {MAX_ATTEMPTS} attempts "
                    f"({last}). Try again in a moment.")


class SyncService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.accounts = AccountRepository(session)
        self.institutions = InstitutionRepository(session)
        self.transactions = TransactionRepository(session)
        self.balances = BalanceRepository(session)
        self.runs = SyncRunRepository(session)
        self.audit = AuditRepository(session)
        self.bus = get_event_bus()
        self.provider = get_provider()

    async def sync(self, user_id: int, user_email: str) -> dict:
        """Run one full incremental sync for this user. Returns an honest summary."""
        user_key = user_email.split("@")[0]
        run_id = await self.runs.start(user_id, self.provider.key)
        cursor_raw = await self.runs.last_cursor(user_id, self.provider.key)
        cursors: dict[str, str] = json.loads(cursor_raw) if cursor_raw else {}
        await self.session.commit()
        self.bus.publish(user_id, "sync.started", {"run_id": run_id})

        per_account: list[dict] = []
        total_new = 0
        failures = 0
        try:
            provider_accounts = await _with_retry(
                lambda: self.provider.list_accounts(user_key), "Listing accounts")
            for dto in provider_accounts:
                try:
                    account_id = await self._upsert_account(user_id, dto)
                    new_count, cursors[dto.key] = await self._sync_transactions(
                        user_id, account_id, user_key, dto.key,
                        cursors.get(dto.key))
                    total_new += new_count
                    entry = {"account_key": dto.key,
                             "display_name": dto.display_name,
                             "status": "ok", "new_transactions": new_count}
                    try:
                        # Transactions are already ingested; a balance refresh
                        # failure degrades the entry, it doesn't undo the sync.
                        await self._record_balance(user_id, account_id,
                                                   user_key, dto.key)
                    except SyncError as exc:
                        entry["balance_error"] = exc.message
                    per_account.append(entry)
                    self.bus.publish(user_id, "sync.account_done", entry)
                except SyncError as exc:
                    failures += 1
                    per_account.append({"account_key": dto.key,
                                        "display_name": dto.display_name,
                                        "status": "failed", "error": exc.message})
                    self.bus.publish(user_id, "sync.account_done", per_account[-1])

            status = "succeeded" if failures == 0 else \
                ("partial" if failures < len(provider_accounts) else "failed")
            await self.runs.finish(user_id, run_id, status=status,
                                   cursor=json.dumps(cursors),
                                   records_ingested=total_new,
                                   error=None if failures == 0 else
                                   f"{failures} account(s) failed")
            await self.audit.append(user_id, event="sync.completed",
                                    detail={"run_id": run_id, "status": status,
                                            "new": total_new})
            await self.session.commit()
            summary = {"run_id": run_id, "status": status,
                       "new_transactions": total_new, "accounts": per_account}
            self.bus.publish(user_id, "sync.completed", summary)
            if total_new:
                self.bus.publish(user_id, "transactions.new", {"count": total_new})
            return summary
        except SyncError as exc:
            await self.runs.finish(user_id, run_id, status="failed",
                                   cursor=json.dumps(cursors),
                                   records_ingested=total_new, error=exc.message)
            await self.session.commit()
            self.bus.publish(user_id, "sync.failed",
                             {"run_id": run_id, "error": exc.message})
            raise

    async def status(self, user_id: int) -> dict:
        run = await self.runs.last(user_id, self.provider.key)
        if run is None:
            return {"provider": self.provider.key, "last_run": None}
        return {"provider": self.provider.key, "last_run": {
            "run_id": run.id, "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "records_ingested": run.records_ingested,
            "error": run.error,
        }}

    # -- Internals ---------------------------------------------------------

    async def _upsert_account(self, user_id: int, dto: AccountDTO) -> int:
        existing = await self.accounts.get_by_provider_key(user_id, dto.key)
        if existing is None:
            # A statement import may have created this account before the first
            # sync — adopt it rather than duplicating it.
            existing = await self.accounts.adopt_provider_key(
                user_id, provider_key=dto.key, mask=dto.mask, type=dto.type,
                display_name=dto.display_name)
        if existing is not None:
            if dto.closed_at and existing.closed_at is None:
                await self.accounts.mark_closed(user_id, existing.id, dto.closed_at)
            return existing.id
        institutions = await self.institutions.list(user_id)
        inst = next((i for i in institutions if i.name == dto.institution), None)
        inst_id = inst.id if inst else await self.institutions.create(
            user_id, name=dto.institution, kind=dto.institution_kind,
            provider_key=self.provider.key)
        return await self.accounts.create(
            user_id, institution_id=inst_id, display_name=dto.display_name,
            type=dto.type, mask=dto.mask, currency=dto.currency,
            is_liquid=dto.is_liquid, provider_key=dto.key, closed_at=dto.closed_at)

    async def _sync_transactions(self, user_id: int, account_id: int, user_key: str,
                                 account_key: str, cursor: str | None) -> tuple[int, str]:
        new_rows: list[TransactionDTO] = []
        while True:
            page = await _with_retry(
                lambda: self.provider.fetch_transactions(user_key, account_key, cursor),
                f"Fetching transactions for {account_key}")
            new_rows.extend(page.transactions)
            cursor = page.next_cursor
            if not page.has_more:
                break

        if not new_rows:
            return 0, cursor or "0"

        known_ids = await self.transactions.existing_external_ids(user_id, account_id)
        fresh = [t for t in new_rows if t.external_id not in known_ids]
        if not fresh:
            return 0, cursor or "0"

        window_from = min(t.date for t in fresh) - dt.timedelta(days=4)
        window_to = max(t.date for t in fresh) + dt.timedelta(days=4)
        existing_rows = await self.transactions.list_for_matching(
            user_id, account_id=account_id, date_from=window_from, date_to=window_to)
        matcher_existing = [
            Existing(id=r.id, posted_date=r.posted_date, amount_minor=r.amount_minor,
                     description=r.description_raw, dedupe_hash=r.dedupe_hash)
            for r in existing_rows if r.external_id is None
        ]
        incoming = [Incoming(index=i, posted_date=t.date, amount_minor=t.amount_minor,
                             description=t.description)
                    for i, t in enumerate(fresh)]
        result = match_incoming(account_id, incoming, matcher_existing)

        for index, existing_id in result.merged.items():
            t = fresh[index]
            await self.transactions.attach_external_id(
                user_id, existing_id, t.external_id, merchant=t.merchant,
                provider_date=t.date)
        inserted = 0
        for index in result.to_insert:
            t = fresh[index]
            await self.transactions.create(
                user_id, account_id=account_id, posted_date=t.date,
                description_raw=t.description, amount_minor=t.amount_minor,
                type=t.type, source="provider",
                dedupe_hash=dedupe_hash(account_id, t.date, t.amount_minor,
                                        t.description),
                external_id=t.external_id, merchant=t.merchant, pending=t.pending)
            inserted += 1
        return inserted, cursor or "0"

    async def _record_balance(self, user_id: int, account_id: int, user_key: str,
                              account_key: str) -> None:
        balance = await _with_retry(
            lambda: self.provider.fetch_balances(user_key, account_key),
            f"Fetching balance for {account_key}")
        await self.balances.record(
            user_id, account_id=account_id, as_of=balance.as_of,
            current_minor=balance.current_minor,
            available_minor=balance.available_minor, source="provider")
