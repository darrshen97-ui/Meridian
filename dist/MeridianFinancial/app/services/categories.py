"""System category taxonomy (docs/DECISIONS.md D-006).

A fixed system set keeps LLM output validation strict and the demo profiles
comparable; users add their own categories beneath it.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category

SYSTEM_CATEGORIES = [
    "Income", "Housing", "Utilities", "Groceries", "Dining", "Transport",
    "Subscriptions", "Insurance", "Health", "Travel", "Shopping", "Entertainment",
    "Education", "Fees", "Transfers", "Crypto", "Loan Payments", "Cash", "Taxes",
    "Uncategorized",
]


async def ensure_system_categories(session: AsyncSession) -> None:
    """Idempotent: inserts any missing system categories."""
    existing = set(await session.scalars(
        select(Category.name).where(Category.is_system.is_(True))))
    for name in SYSTEM_CATEGORIES:
        if name not in existing:
            session.add(Category(user_id=None, name=name, is_system=True))
    await session.commit()
