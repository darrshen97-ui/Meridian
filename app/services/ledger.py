"""Read services for the ledger views. All operations are scoped to one user."""
from __future__ import annotations

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    AccountInfo,
    BudgetInfo,
    CategoryInfo,
    DocumentInfo,
    InstitutionInfo,
    TransactionInfo,
)
from app.repositories.audit import AuditRepository
from app.repositories.ledger import (
    AccountRepository,
    BudgetRepository,
    CategoryRepository,
    DocumentListRepository,
    InstitutionRepository,
    TransactionRepository,
    UserCorrectionRepository,
)
from app.services.dedupe import normalize_description


class LedgerError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class LedgerService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.institutions = InstitutionRepository(session)
        self.accounts = AccountRepository(session)
        self.transactions = TransactionRepository(session)
        self.categories = CategoryRepository(session)
        self.documents = DocumentListRepository(session)
        self.budgets = BudgetRepository(session)

    async def list_institutions(self, user_id: int) -> list[InstitutionInfo]:
        return await self.institutions.list(user_id)

    async def list_accounts(self, user_id: int) -> list[AccountInfo]:
        return await self.accounts.list(user_id)

    async def list_transactions(self, user_id: int, *, account_id: int | None = None,
                                date_from: dt.date | None = None,
                                date_to: dt.date | None = None,
                                q: str | None = None, category_id: int | None = None,
                                source: str | None = None, uncategorized: bool = False,
                                limit: int = 200, offset: int = 0) -> list[TransactionInfo]:
        return await self.transactions.list(
            user_id, account_id=account_id, date_from=date_from, date_to=date_to,
            q=q, category_id=category_id, source=source, uncategorized=uncategorized,
            limit=min(limit, 500), offset=offset,
        )

    async def list_categories(self, user_id: int) -> list[CategoryInfo]:
        return await self.categories.list(user_id)

    async def list_documents(self, user_id: int) -> list[DocumentInfo]:
        return await self.documents.list(user_id)

    async def list_budgets(self, user_id: int) -> list[BudgetInfo]:
        return await self.budgets.list(user_id)

    async def set_transaction_category(self, user_id: int, transaction_id: int,
                                       category_id: int) -> TransactionInfo:
        """A user override: authoritative, and it teaches the rules pass (tier 1)."""
        category = await self.categories.get_visible(user_id, category_id)
        if category is None:
            raise LedgerError("That category doesn't exist.", status_code=404)
        updated = await self.transactions.set_category(
            user_id, transaction_id, category_id=category_id,
            source="user", confidence=1.0, mark_reviewed=True)
        if updated is None:
            raise LedgerError("That transaction doesn't exist.", status_code=404)

        pattern = normalize_description(updated.merchant or updated.description_raw)
        corrections = UserCorrectionRepository(self.session)
        await corrections.add(user_id, merchant_pattern=pattern,
                              category_id=category_id)
        await AuditRepository(self.session).append(
            user_id, event="category.overridden",
            detail={"transaction_id": transaction_id, "category_id": category_id,
                    "pattern": pattern})
        await self.session.commit()
        return updated
