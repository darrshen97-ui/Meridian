"""Core types and helpers for the mock dataset generator.

Everything is deterministic: a fixed seed, a fixed reference "today"
(2026-08-09, per docs/DECISIONS.md D-004), and no wall-clock reads anywhere.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, replace

SEED = 20260809
TODAY = dt.date(2026, 8, 9)          # the dataset's pinned "now"
PERIOD_START = dt.date(2025, 8, 1)   # first statement day
PERIOD_END = dt.date(2026, 7, 31)    # last statement day; Aug 1-9 2026 is provider-only

STATEMENT_MONTHS: list[tuple[int, int]] = [
    (2025, m) for m in range(8, 13)
] + [(2026, m) for m in range(1, 8)]


@dataclass
class AccountSpec:
    key: str
    institution: str
    institution_kind: str
    display_name: str
    mask: str | None
    type: str
    is_liquid: bool
    opening_balance_minor: int  # balance at PERIOD_START (negative = owed)
    opened_at: dt.date | None = None
    closed_at: dt.date | None = None
    closed_reason: str | None = None
    currency: str = "USD"


@dataclass
class Txn:
    account: str
    date: dt.date                     # the provider/actual date
    description: str
    amount_minor: int                 # signed; negative = money out of the account
    type: str = "debit"               # debit | credit | transfer
    merchant: str | None = None
    category: str = ""                # ground-truth hint (guide + tests only)
    statement_date: dt.date | None = None  # differs from date only for the shift trio
    in_statement: bool = True
    in_provider: bool = True
    pending: bool = False
    event: str = ""                   # planted-event tag, "" for ordinary rows
    external_id: str = ""
    seq: int = 0

    @property
    def stmt_date(self) -> dt.date:
        return self.statement_date or self.date


@dataclass
class Ledger:
    profile_key: str
    display_name: str
    email: str
    password: str  # demo credential, documented in DATASET_GUIDE.md
    accounts: list[AccountSpec]
    txns: list[Txn] = field(default_factory=list)

    def add(self, account: str, date: dt.date, description: str, amount_minor: int,
            **kw) -> Txn:
        txn = Txn(account=account, date=date, description=description,
                  amount_minor=amount_minor, **kw)
        self.txns.append(txn)
        return txn

    def account(self, key: str) -> AccountSpec:
        return next(a for a in self.accounts if a.key == key)

    def finalize(self) -> None:
        """Stable ordering, external ids, and a floor on liquid balances."""
        self.txns.sort(key=lambda t: (t.date, t.account, t.seq, t.description))
        counters: dict[str, int] = {}
        for t in self.txns:
            counters[t.account] = counters.get(t.account, 0) + 1
            t.external_id = f"{self.profile_key}-{t.account}-{counters[t.account]:05d}"

        # Depository-style balances must never dip below a small floor; if the random
        # draw would take one negative, raise its opening balance deterministically.
        for spec in self.accounts:
            if spec.type in ("credit_card", "loan"):
                continue
            floor = 20_00  # $20.00
            running = spec.opening_balance_minor
            low = running
            for t in self.txns:
                if t.account == spec.key and not t.pending:
                    running += t.amount_minor
                    low = min(low, running)
            if low < floor:
                spec.opening_balance_minor += floor - low

    # -- Views ------------------------------------------------------------

    def statement_txns(self, account: str, year: int, month: int) -> list[Txn]:
        return sorted(
            (t for t in self.txns
             if t.account == account and t.in_statement and not t.pending
             and t.stmt_date.year == year and t.stmt_date.month == month),
            key=lambda t: (t.stmt_date, t.seq, t.description),
        )

    def provider_txns(self, account: str | None = None) -> list[Txn]:
        return [t for t in self.txns
                if t.in_provider and (account is None or t.account == account)]

    def balance_before(self, account: str, day: dt.date) -> int:
        """Statement-view balance at the start of `day`."""
        spec = self.account(account)
        total = spec.opening_balance_minor
        for t in self.txns:
            if t.account == account and t.in_statement and not t.pending \
                    and t.stmt_date < day:
                total += t.amount_minor
        return total


def c(dollars: float) -> int:
    """Dollars → integer minor units. Only for literal constants in this generator."""
    return round(dollars * 100)


def fmt_money(minor: int) -> str:
    """Integer-only money formatting: 123456 → '1,234.56'."""
    sign = "-" if minor < 0 else ""
    a = abs(minor)
    return f"{sign}{a // 100:,}.{a % 100:02d}"


def month_days(year: int, month: int) -> tuple[dt.date, dt.date]:
    first = dt.date(year, month, 1)
    last = (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    return first, last


def mondays_between(start: dt.date, end: dt.date) -> list[dt.date]:
    d = start + dt.timedelta(days=(7 - start.weekday()) % 7)
    out = []
    while d <= end:
        out.append(d)
        d += dt.timedelta(days=7)
    return out


def biweekly(start: dt.date, end: dt.date) -> list[dt.date]:
    out, d = [], start
    while d <= end:
        out.append(d)
        d += dt.timedelta(days=14)
    return out
