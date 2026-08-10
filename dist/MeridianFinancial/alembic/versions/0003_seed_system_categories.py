"""Seed the system category taxonomy (D-006).

Revision ID: 8b1c2d3e4f50
Revises: 57577f2e206e
Create Date: 2026-08-09

Data migration: inserts the fixed system categories every profile shares.
Reversible: downgrade removes exactly the system rows it inserted.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "8b1c2d3e4f50"
down_revision = "57577f2e206e"
branch_labels = None
depends_on = None

SYSTEM_CATEGORIES = [
    "Income", "Housing", "Utilities", "Groceries", "Dining", "Transport",
    "Subscriptions", "Insurance", "Health", "Travel", "Shopping", "Entertainment",
    "Education", "Fees", "Transfers", "Crypto", "Loan Payments", "Cash", "Taxes",
    "Uncategorized",
]

categories = sa.table(
    "categories",
    sa.column("user_id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("parent_id", sa.Integer),
    sa.column("is_system", sa.Boolean),
)


def upgrade() -> None:
    op.bulk_insert(categories, [
        {"user_id": None, "name": name, "parent_id": None, "is_system": True}
        for name in SYSTEM_CATEGORIES
    ])


def downgrade() -> None:
    op.execute(
        categories.delete().where(
            sa.and_(categories.c.is_system == sa.true(),
                    categories.c.name.in_(SYSTEM_CATEGORIES)))
    )
