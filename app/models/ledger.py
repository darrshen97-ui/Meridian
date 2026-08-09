"""Institutions, accounts, balances, transactions, categories, corrections, budgets.

All money columns are integer minor units (cents). All timestamps are UTC.
Kind/type/status columns are constrained strings rather than native enums so the
schema stays in the SQLite ∩ PostgreSQL intersection (see docs/DECISIONS.md D-001).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow

INSTITUTION_KINDS = ("bank", "credit", "payment_app", "exchange", "loan")
INSTITUTION_STATUSES = ("active", "closed")
ACCOUNT_TYPES = ("checking", "savings", "credit_card", "loan", "crypto", "payment_app")
TRANSACTION_TYPES = ("debit", "credit", "transfer")
TRANSACTION_SOURCES = ("statement", "provider", "manual")
CATEGORY_SOURCES = ("rules", "llm", "user")


class Institution(Base):
    __tablename__ = "institutions"
    __table_args__ = (
        CheckConstraint(f"kind IN {INSTITUTION_KINDS}", name="kind"),
        CheckConstraint(f"status IN {INSTITUTION_STATUSES}", name="status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20))
    provider_key: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="active")
    closed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    closed_reason: Mapped[str | None] = mapped_column(String(255))


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (CheckConstraint(f"type IN {ACCOUNT_TYPES}", name="type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"))
    display_name: Mapped[str] = mapped_column(String(120))
    mask: Mapped[str | None] = mapped_column(String(4))
    type: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    is_liquid: Mapped[bool] = mapped_column(Boolean, default=False)  # drives spending power
    opened_at: Mapped[dt.date | None] = mapped_column(Date)
    closed_at: Mapped[dt.date | None] = mapped_column(Date)


class Balance(Base):
    __tablename__ = "balances"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    as_of: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    current_minor: Mapped[int] = mapped_column(BigInteger)
    available_minor: Mapped[int | None] = mapped_column(BigInteger)
    source: Mapped[str] = mapped_column(String(20))


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    # NULL user_id = system category, visible to every profile.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(f"type IN {TRANSACTION_TYPES}", name="type"),
        CheckConstraint(f"source IN {TRANSACTION_SOURCES}", name="source"),
        Index("ix_transactions_user_posted", "user_id", "posted_date"),
        Index("ix_transactions_dedupe", "account_id", "dedupe_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    posted_date: Mapped[dt.date] = mapped_column(Date)
    transaction_date: Mapped[dt.date | None] = mapped_column(Date)
    description_raw: Mapped[str] = mapped_column(Text)
    description_clean: Mapped[str | None] = mapped_column(Text)
    merchant: Mapped[str | None] = mapped_column(String(120), index=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger)  # signed; never a float
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    type: Mapped[str] = mapped_column(String(20))
    pending: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20))
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))
    external_id: Mapped[str | None] = mapped_column(String(120), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    category_confidence: Mapped[float | None] = mapped_column(Float)
    category_source: Mapped[str | None] = mapped_column(String(20))
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    dedupe_hash: Mapped[str] = mapped_column(String(64))


class UserCorrection(Base):
    __tablename__ = "user_corrections"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    merchant_pattern: Mapped[str] = mapped_column(String(120))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    period_type: Mapped[str] = mapped_column(String(20), default="monthly")
    period_start: Mapped[dt.date] = mapped_column(Date)
    target_minor: Mapped[int] = mapped_column(BigInteger)
