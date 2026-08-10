"""PlaidProvider — deliberate Iteration 2 stub (brief §3, §11).

The sync machinery is proven against MockProvider first; wiring Plaid in is a
provider swap, not an architecture change. Method-to-endpoint mapping:

  * list_accounts       → POST /accounts/get  (account_id, name, mask, type,
                          subtype, balances) — map subtype onto our account types
  * fetch_transactions  → POST /transactions/sync  (cursor-based; `next_cursor`
                          maps directly onto our TransactionPage.next_cursor,
                          `added`/`modified`/`removed` onto the ingest stream)
  * fetch_balances      → POST /accounts/balance/get  (real-time balances)

Auth (link tokens, item management) belongs to a separate onboarding flow, not
this read interface.
"""
from __future__ import annotations

from app.providers.financial.base import (
    AccountDTO,
    BalanceDTO,
    TransactionPage,
)


class PlaidProvider:
    key = "plaid"

    async def list_accounts(self, user_key: str) -> list[AccountDTO]:
        raise NotImplementedError(
            "Plaid integration is deferred to Iteration 2 by design. "
            "See docs/BUILD_PLAN.md §1 (out of scope).")

    async def fetch_transactions(self, user_key: str, account_key: str,
                                 cursor: str | None) -> TransactionPage:
        raise NotImplementedError(
            "Plaid integration is deferred to Iteration 2 by design.")

    async def fetch_balances(self, user_key: str, account_key: str) -> BalanceDTO:
        raise NotImplementedError(
            "Plaid integration is deferred to Iteration 2 by design.")
