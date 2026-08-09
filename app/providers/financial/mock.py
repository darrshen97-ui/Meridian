"""MockProvider — serves the generated ledger through a simulated provider API.

Realistic behavior on purpose (brief §11): cursor-based pagination, 200-900ms
simulated latency, a configurable transient-failure rate, and occasional 429s,
so the sync layer's retry/backoff/error-surfacing code is actually exercised.

State (injected "simulated incoming" transactions, cursors served) lives for
the process lifetime in a module singleton.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import random
from pathlib import Path

from app.providers.financial.base import (
    AccountDTO,
    BalanceDTO,
    ProviderRateLimited,
    ProviderTransientError,
    TransactionDTO,
    TransactionPage,
)

PAGE_SIZE = 200
SIM_MERCHANT_POOL = [
    ("SQ *BLUE STEM", -1275), ("GRUBHUB PDXEATS", -3240),
    ("SHELL OIL 57444829", -4810), ("AMZN MKTP US*", -2699),
    ("SAFEWAY #1442 PORTLAND OR", -6432), ("TST* MERIDIAN 04", -1140),
]


class MockProvider:
    key = "mock"

    def __init__(self, fixtures_dir: Path, *,
                 min_latency: float = 0.2, max_latency: float = 0.9,
                 failure_rate: float = 0.05, rate_limit_every: int = 37):
        self.fixtures_dir = fixtures_dir
        self.min_latency = min_latency
        self.max_latency = max_latency
        self.failure_rate = failure_rate
        self.rate_limit_every = rate_limit_every
        self._chaos = random.Random(20260809)
        self._calls = 0
        self._fixtures: dict[str, dict] = {}
        self._injected: dict[str, list[TransactionDTO]] = {}
        self._sim_counter = 0

    # -- Simulated API behavior -------------------------------------------

    async def _api_call(self) -> None:
        self._calls += 1
        if self.max_latency > 0:
            await asyncio.sleep(self._chaos.uniform(self.min_latency, self.max_latency))
        if self.rate_limit_every and self._calls % self.rate_limit_every == 0:
            raise ProviderRateLimited(retry_after=0.2)
        if self._chaos.random() < self.failure_rate:
            raise ProviderTransientError("simulated upstream hiccup")

    def _fixture(self, user_key: str) -> dict | None:
        if user_key not in self._fixtures:
            path = self.fixtures_dir / f"{user_key}.json"
            self._fixtures[user_key] = json.loads(path.read_text()) if path.exists() \
                else {}
        return self._fixtures[user_key] or None

    def _stream(self, user_key: str, account_key: str) -> list[TransactionDTO]:
        """The account's append-only transaction stream (fixture + injected)."""
        fixture = self._fixture(user_key)
        if not fixture:
            return []
        base = [
            TransactionDTO(
                external_id=t["external_id"], account_key=t["account"],
                date=dt.date.fromisoformat(t["date"]), description=t["description"],
                amount_minor=t["amount_minor"], type=t["type"],
                pending=t["pending"], merchant=t.get("merchant"),
            )
            for t in fixture["transactions"] if t["account"] == account_key
        ]
        injected = [t for t in self._injected.get(user_key, [])
                    if t.account_key == account_key]
        return base + injected

    # -- FinancialDataProvider --------------------------------------------

    async def list_accounts(self, user_key: str) -> list[AccountDTO]:
        await self._api_call()
        fixture = self._fixture(user_key)
        if not fixture:
            return []
        kinds = {i["name"]: i["kind"] for i in fixture["institutions"]}
        return [
            AccountDTO(
                key=a["key"], institution=a["institution"],
                institution_kind=kinds[a["institution"]],
                display_name=a["display_name"], mask=a["mask"], type=a["type"],
                currency=a["currency"], is_liquid=a["is_liquid"],
                closed_at=dt.date.fromisoformat(a["closed_at"]) if a["closed_at"]
                else None,
                closed_reason=a["closed_reason"],
            )
            for a in fixture["accounts"]
        ]

    async def fetch_transactions(self, user_key: str, account_key: str,
                                 cursor: str | None) -> TransactionPage:
        await self._api_call()
        stream = self._stream(user_key, account_key)
        offset = int(cursor) if cursor else 0
        page = stream[offset:offset + PAGE_SIZE]
        next_offset = offset + len(page)
        return TransactionPage(
            transactions=page,
            next_cursor=str(next_offset),
            has_more=next_offset < len(stream),
        )

    async def fetch_balances(self, user_key: str, account_key: str) -> BalanceDTO:
        await self._api_call()
        fixture = self._fixture(user_key)
        account = next(a for a in fixture["accounts"] if a["key"] == account_key)
        injected = sum(t.amount_minor for t in self._injected.get(user_key, [])
                       if t.account_key == account_key and not t.pending)
        current = account["current_balance_minor"] + injected
        return BalanceDTO(
            current_minor=current, available_minor=current,
            as_of=dt.datetime.fromisoformat(fixture["as_of"] + "T00:00:00+00:00"),
        )

    # -- Dev tooling (Settings → "Simulate incoming transactions") ---------

    def inject_transactions(self, user_key: str, count: int) -> list[TransactionDTO]:
        fixture = self._fixture(user_key)
        if not fixture:
            return []
        as_of = dt.date.fromisoformat(fixture["as_of"])
        spendable = [a["key"] for a in fixture["accounts"]
                     if a["type"] in ("checking", "credit_card") and not a["closed_at"]]
        out = []
        for _ in range(count):
            self._sim_counter += 1
            desc, cents = self._chaos.choice(SIM_MERCHANT_POOL)
            jitter = self._chaos.randint(-300, 300)
            out.append(TransactionDTO(
                external_id=f"{user_key}-sim-{self._sim_counter:04d}",
                account_key=self._chaos.choice(spendable),
                date=as_of,
                description=desc,
                amount_minor=cents + jitter,
                type="debit",
            ))
        self._injected.setdefault(user_key, []).extend(out)
        return out
