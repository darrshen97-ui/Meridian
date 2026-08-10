"""FinancialDataProvider protocol (brief §11) and its DTOs.

Iteration 2 swaps MockProvider for PlaidProvider behind this same interface —
the sync machinery must not know which one it's talking to.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AccountDTO:
    key: str                       # the provider's stable account identity
    institution: str
    institution_kind: str
    display_name: str
    mask: str | None
    type: str
    currency: str
    is_liquid: bool
    closed_at: dt.date | None = None
    closed_reason: str | None = None


@dataclass(frozen=True)
class BalanceDTO:
    current_minor: int
    available_minor: int | None
    as_of: dt.datetime


@dataclass(frozen=True)
class TransactionDTO:
    external_id: str
    account_key: str
    date: dt.date
    description: str
    amount_minor: int
    type: str                      # debit | credit | transfer
    pending: bool = False
    merchant: str | None = None


@dataclass(frozen=True)
class TransactionPage:
    transactions: list[TransactionDTO]
    next_cursor: str | None
    has_more: bool


class ProviderTransientError(Exception):
    """Retryable: the provider hiccuped (network blip, 5xx)."""


class ProviderRateLimited(Exception):
    """Retryable after a delay: the provider returned 429."""

    def __init__(self, retry_after: float = 1.0):
        super().__init__(f"rate limited; retry after {retry_after}s")
        self.retry_after = retry_after


class FinancialDataProvider(Protocol):
    key: str  # recorded in sync_runs.provider_key

    async def list_accounts(self, user_key: str) -> list[AccountDTO]: ...

    async def fetch_transactions(
        self, user_key: str, account_key: str, cursor: str | None
    ) -> TransactionPage: ...

    async def fetch_balances(self, user_key: str, account_key: str) -> BalanceDTO: ...
