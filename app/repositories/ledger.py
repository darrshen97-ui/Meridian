"""User-scoped repositories for the financial ledger.

Every public method takes `user_id` as its first argument and filters on it.
No exceptions — enforced by tests/test_repo_signatures.py.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    AccountInfo,
    BudgetInfo,
    CategoryInfo,
    DocumentInfo,
    InstitutionInfo,
    TransactionInfo,
)
from app.models import Account, Budget, Category, Document, Institution, Transaction


class InstitutionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, user_id: int) -> list[InstitutionInfo]:
        rows = await self.session.scalars(
            select(Institution).where(Institution.user_id == user_id).order_by(Institution.name)
        )
        return [
            InstitutionInfo(
                id=r.id, name=r.name, kind=r.kind, status=r.status,
                closed_at=r.closed_at, closed_reason=r.closed_reason,
            )
            for r in rows
        ]

    async def create(self, user_id: int, *, name: str, kind: str,
                     provider_key: str | None = None) -> int:
        row = Institution(user_id=user_id, name=name, kind=kind, provider_key=provider_key)
        self.session.add(row)
        await self.session.flush()
        return row.id


class AccountRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, user_id: int) -> list[AccountInfo]:
        rows = await self.session.scalars(
            select(Account).where(Account.user_id == user_id).order_by(Account.display_name)
        )
        return [self._map(r) for r in rows]

    async def get(self, user_id: int, account_id: int) -> AccountInfo | None:
        row = await self.session.scalar(
            select(Account).where(Account.user_id == user_id, Account.id == account_id)
        )
        return self._map(row) if row else None

    async def create(self, user_id: int, *, institution_id: int, display_name: str,
                     type: str, mask: str | None = None, currency: str = "USD",
                     is_liquid: bool = False, opened_at: dt.date | None = None) -> int:
        row = Account(
            user_id=user_id, institution_id=institution_id, display_name=display_name,
            type=type, mask=mask, currency=currency, is_liquid=is_liquid, opened_at=opened_at,
        )
        self.session.add(row)
        await self.session.flush()
        return row.id

    @staticmethod
    def _map(r: Account) -> AccountInfo:
        return AccountInfo(
            id=r.id, institution_id=r.institution_id, display_name=r.display_name,
            mask=r.mask, type=r.type, currency=r.currency, is_liquid=r.is_liquid,
            opened_at=r.opened_at, closed_at=r.closed_at,
        )


class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, user_id: int, *, account_id: int | None = None,
                   date_from: dt.date | None = None, date_to: dt.date | None = None,
                   limit: int = 200, offset: int = 0) -> list[TransactionInfo]:
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        if account_id is not None:
            stmt = stmt.where(Transaction.account_id == account_id)
        if date_from is not None:
            stmt = stmt.where(Transaction.posted_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Transaction.posted_date <= date_to)
        stmt = stmt.order_by(Transaction.posted_date.desc(), Transaction.id.desc())
        stmt = stmt.limit(limit).offset(offset)
        rows = await self.session.scalars(stmt)
        return [self._map(r) for r in rows]

    async def create(self, user_id: int, *, account_id: int, posted_date: dt.date,
                     description_raw: str, amount_minor: int, type: str, source: str,
                     dedupe_hash: str, **extra) -> int:
        row = Transaction(
            user_id=user_id, account_id=account_id, posted_date=posted_date,
            description_raw=description_raw, amount_minor=amount_minor, type=type,
            source=source, dedupe_hash=dedupe_hash, **extra,
        )
        self.session.add(row)
        await self.session.flush()
        return row.id

    async def list_for_matching(self, user_id: int, *, account_id: int,
                                date_from: dt.date, date_to: dt.date) -> list[Transaction]:
        """ORM rows for the dedupe matcher (internal to services; not for routers)."""
        rows = await self.session.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.account_id == account_id,
                Transaction.posted_date >= date_from,
                Transaction.posted_date <= date_to,
            )
        )
        return list(rows)

    async def list_by_document(self, user_id: int, document_id: int) -> list[TransactionInfo]:
        rows = await self.session.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.source_document_id == document_id,
            ).order_by(Transaction.posted_date, Transaction.id)
        )
        return [self._map(r) for r in rows]

    async def attach_document(self, user_id: int, transaction_id: int,
                              document_id: int) -> None:
        """Record the statement source on a row that already exists from another source."""
        row = await self.session.scalar(
            select(Transaction).where(Transaction.user_id == user_id,
                                      Transaction.id == transaction_id))
        if row is not None and row.source_document_id is None:
            row.source_document_id = document_id

    @staticmethod
    def _map(r: Transaction) -> TransactionInfo:
        return TransactionInfo(
            id=r.id, account_id=r.account_id, posted_date=r.posted_date,
            transaction_date=r.transaction_date, description_raw=r.description_raw,
            description_clean=r.description_clean, merchant=r.merchant,
            amount_minor=r.amount_minor, currency=r.currency, type=r.type,
            pending=r.pending, source=r.source, source_document_id=r.source_document_id,
            category_id=r.category_id, category_confidence=r.category_confidence,
            category_source=r.category_source, reviewed_at=r.reviewed_at,
        )


class CategoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, user_id: int) -> list[CategoryInfo]:
        """System categories plus this user's own — never another user's."""
        rows = await self.session.scalars(
            select(Category)
            .where(or_(Category.user_id == user_id, Category.user_id.is_(None)))
            .order_by(Category.name)
        )
        return [
            CategoryInfo(id=r.id, name=r.name, parent_id=r.parent_id, is_system=r.is_system)
            for r in rows
        ]

    async def create(self, user_id: int, *, name: str,
                     parent_id: int | None = None) -> int:
        row = Category(user_id=user_id, name=name, parent_id=parent_id, is_system=False)
        self.session.add(row)
        await self.session.flush()
        return row.id


class DocumentListRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, user_id: int) -> list[DocumentInfo]:
        rows = await self.session.scalars(
            select(Document).where(Document.user_id == user_id).order_by(Document.uploaded_at.desc())
        )
        return [
            DocumentInfo(
                id=r.id, account_id=r.account_id, kind=r.kind, filename=r.filename,
                period_start=r.period_start, period_end=r.period_end,
                parse_status=r.parse_status, parse_error=r.parse_error, uploaded_at=r.uploaded_at,
            )
            for r in rows
        ]


class BudgetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, user_id: int) -> list[BudgetInfo]:
        rows = await self.session.scalars(select(Budget).where(Budget.user_id == user_id))
        return [
            BudgetInfo(
                id=r.id, category_id=r.category_id, period_type=r.period_type,
                period_start=r.period_start, target_minor=r.target_minor,
            )
            for r in rows
        ]
