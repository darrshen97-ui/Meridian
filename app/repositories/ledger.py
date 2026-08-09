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
from app.models import (
    Account,
    Budget,
    Category,
    Document,
    Institution,
    Transaction,
    UserCorrection,
)


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

    async def get_by_provider_key(self, user_id: int, provider_key: str) -> AccountInfo | None:
        row = await self.session.scalar(
            select(Account).where(Account.user_id == user_id,
                                  Account.provider_key == provider_key))
        return self._map(row) if row else None

    async def adopt_provider_key(self, user_id: int, *, provider_key: str,
                                 mask: str | None, type: str,
                                 display_name: str) -> AccountInfo | None:
        """Link a provider account to one created earlier from a statement.

        Match by mask+type when the document carried a mask; otherwise by
        type+display name (payment apps and exchanges have no mask).
        """
        stmt = select(Account).where(Account.user_id == user_id,
                                     Account.provider_key.is_(None),
                                     Account.type == type)
        if mask:
            stmt = stmt.where(Account.mask == mask)
        else:
            stmt = stmt.where(Account.display_name == display_name)
        row = await self.session.scalar(stmt)
        if row is None:
            return None
        row.provider_key = provider_key
        return self._map(row)

    async def mark_closed(self, user_id: int, account_id: int,
                          closed_at: dt.date) -> None:
        row = await self.session.scalar(
            select(Account).where(Account.user_id == user_id,
                                  Account.id == account_id))
        if row is not None and row.closed_at is None:
            row.closed_at = closed_at

    async def create(self, user_id: int, *, institution_id: int, display_name: str,
                     type: str, mask: str | None = None, currency: str = "USD",
                     is_liquid: bool = False, opened_at: dt.date | None = None,
                     provider_key: str | None = None,
                     closed_at: dt.date | None = None) -> int:
        row = Account(
            user_id=user_id, institution_id=institution_id, display_name=display_name,
            type=type, mask=mask, currency=currency, is_liquid=is_liquid,
            opened_at=opened_at, provider_key=provider_key, closed_at=closed_at,
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
                   q: str | None = None, category_id: int | None = None,
                   source: str | None = None, uncategorized: bool = False,
                   limit: int = 200, offset: int = 0) -> list[TransactionInfo]:
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        if account_id is not None:
            stmt = stmt.where(Transaction.account_id == account_id)
        if date_from is not None:
            stmt = stmt.where(Transaction.posted_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Transaction.posted_date <= date_to)
        if q:
            needle = f"%{q.strip()}%"
            stmt = stmt.where(Transaction.description_raw.ilike(needle)
                              | Transaction.merchant.ilike(needle))
        if category_id is not None:
            stmt = stmt.where(Transaction.category_id == category_id)
        if uncategorized:
            stmt = stmt.where(Transaction.category_id.is_(None))
        if source == "both":
            stmt = stmt.where(Transaction.external_id.is_not(None),
                              Transaction.source_document_id.is_not(None))
        elif source == "statement":
            stmt = stmt.where(Transaction.source_document_id.is_not(None))
        elif source == "provider":
            stmt = stmt.where(Transaction.external_id.is_not(None))
        stmt = stmt.order_by(Transaction.posted_date.desc(), Transaction.id.desc())
        stmt = stmt.limit(limit).offset(offset)
        rows = await self.session.scalars(stmt)
        return [self._map(r) for r in rows]

    async def set_category(self, user_id: int, transaction_id: int, *,
                           category_id: int | None, source: str,
                           confidence: float | None,
                           mark_reviewed: bool) -> TransactionInfo | None:
        row = await self.session.scalar(
            select(Transaction).where(Transaction.user_id == user_id,
                                      Transaction.id == transaction_id))
        if row is None:
            return None
        row.category_id = category_id
        row.category_source = source
        row.category_confidence = confidence
        if mark_reviewed:
            from app.models.base import utcnow

            row.reviewed_at = utcnow()
        return self._map(row)

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
                              document_id: int,
                              statement_date: dt.date | None = None) -> None:
        """Record the statement source on a row that already exists from another
        source. When the statement dated it differently (1-3 day shift), the
        second date is preserved on transaction_date for reconciliation."""
        row = await self.session.scalar(
            select(Transaction).where(Transaction.user_id == user_id,
                                      Transaction.id == transaction_id))
        if row is not None and row.source_document_id is None:
            row.source_document_id = document_id
            if statement_date and statement_date != row.posted_date \
                    and row.transaction_date is None:
                row.transaction_date = statement_date

    async def attach_external_id(self, user_id: int, transaction_id: int,
                                 external_id: str, merchant: str | None = None,
                                 provider_date: dt.date | None = None) -> None:
        """Record the provider identity on a row that came from a statement."""
        row = await self.session.scalar(
            select(Transaction).where(Transaction.user_id == user_id,
                                      Transaction.id == transaction_id))
        if row is not None and row.external_id is None:
            row.external_id = external_id
            if merchant and row.merchant is None:
                row.merchant = merchant
            if provider_date and provider_date != row.posted_date \
                    and row.transaction_date is None:
                row.transaction_date = provider_date

    async def existing_external_ids(self, user_id: int, account_id: int) -> set[str]:
        rows = await self.session.scalars(
            select(Transaction.external_id).where(
                Transaction.user_id == user_id,
                Transaction.account_id == account_id,
                Transaction.external_id.is_not(None)))
        return set(rows)

    @staticmethod
    def _map(r: Transaction) -> TransactionInfo:
        return TransactionInfo(
            id=r.id, account_id=r.account_id, posted_date=r.posted_date,
            transaction_date=r.transaction_date, description_raw=r.description_raw,
            description_clean=r.description_clean, merchant=r.merchant,
            amount_minor=r.amount_minor, currency=r.currency, type=r.type,
            pending=r.pending, source=r.source, source_document_id=r.source_document_id,
            external_id=r.external_id,
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

    async def get_visible(self, user_id: int, category_id: int) -> CategoryInfo | None:
        """A category this user may assign: their own or a system one."""
        row = await self.session.scalar(
            select(Category).where(
                Category.id == category_id,
                or_(Category.user_id == user_id, Category.user_id.is_(None))))
        if row is None:
            return None
        return CategoryInfo(id=row.id, name=row.name, parent_id=row.parent_id,
                            is_system=row.is_system)


class UserCorrectionRepository:
    """Tier-1 learning memory: every override becomes a merchant-pattern rule."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, user_id: int, *, merchant_pattern: str,
                  category_id: int) -> None:
        self.session.add(UserCorrection(user_id=user_id,
                                        merchant_pattern=merchant_pattern,
                                        category_id=category_id))

    async def list(self, user_id: int) -> list[UserCorrection]:
        rows = await self.session.scalars(
            select(UserCorrection).where(UserCorrection.user_id == user_id)
            .order_by(UserCorrection.created_at.desc(), UserCorrection.id.desc()))
        return list(rows)


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
