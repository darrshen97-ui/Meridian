"""Domain objects — what services accept and return.

Routers never see ORM models; repositories map ORM rows into these dataclasses.
Money is always integer minor units.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class UserProfile:
    id: int
    display_name: str
    email: str
    created_at: dt.datetime
    last_login_at: dt.datetime | None


@dataclass(frozen=True)
class ProfileSummary:
    """What the pre-auth welcome screen may see: names only, no ids leak beyond selection."""

    id: int
    display_name: str
    email: str


@dataclass(frozen=True)
class InstitutionInfo:
    id: int
    name: str
    kind: str
    status: str
    closed_at: dt.datetime | None
    closed_reason: str | None


@dataclass(frozen=True)
class AccountInfo:
    id: int
    institution_id: int
    display_name: str
    mask: str | None
    type: str
    currency: str
    is_liquid: bool
    opened_at: dt.date | None
    closed_at: dt.date | None


@dataclass(frozen=True)
class TransactionInfo:
    id: int
    account_id: int
    posted_date: dt.date
    transaction_date: dt.date | None
    description_raw: str
    description_clean: str | None
    merchant: str | None
    amount_minor: int
    currency: str
    type: str
    pending: bool
    source: str
    source_document_id: int | None
    category_id: int | None
    category_confidence: float | None
    category_source: str | None
    reviewed_at: dt.datetime | None


@dataclass(frozen=True)
class CategoryInfo:
    id: int
    name: str
    parent_id: int | None
    is_system: bool


@dataclass(frozen=True)
class DocumentInfo:
    id: int
    account_id: int | None
    kind: str
    filename: str
    period_start: dt.date | None
    period_end: dt.date | None
    parse_status: str
    parse_error: str | None
    uploaded_at: dt.datetime


@dataclass(frozen=True)
class BudgetInfo:
    id: int
    category_id: int
    period_type: str
    period_start: dt.date
    target_minor: int
