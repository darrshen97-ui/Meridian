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
from app.repositories.ledger import (
    AccountRepository,
    BudgetRepository,
    CategoryRepository,
    DocumentRepository,
    InstitutionRepository,
    TransactionRepository,
)


class LedgerService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.institutions = InstitutionRepository(session)
        self.accounts = AccountRepository(session)
        self.transactions = TransactionRepository(session)
        self.categories = CategoryRepository(session)
        self.documents = DocumentRepository(session)
        self.budgets = BudgetRepository(session)

    async def list_institutions(self, user_id: int) -> list[InstitutionInfo]:
        return await self.institutions.list(user_id)

    async def list_accounts(self, user_id: int) -> list[AccountInfo]:
        return await self.accounts.list(user_id)

    async def list_transactions(self, user_id: int, *, account_id: int | None = None,
                                date_from: dt.date | None = None,
                                date_to: dt.date | None = None,
                                limit: int = 200, offset: int = 0) -> list[TransactionInfo]:
        return await self.transactions.list(
            user_id, account_id=account_id, date_from=date_from, date_to=date_to,
            limit=min(limit, 500), offset=offset,
        )

    async def list_categories(self, user_id: int) -> list[CategoryInfo]:
        return await self.categories.list(user_id)

    async def list_documents(self, user_id: int) -> list[DocumentInfo]:
        return await self.documents.list(user_id)

    async def list_budgets(self, user_id: int) -> list[BudgetInfo]:
        return await self.budgets.list(user_id)
