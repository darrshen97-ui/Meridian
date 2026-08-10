"""The StatementParser protocol, its result types, and the parser registry.

One parser class per format/institution, registered in PARSERS. Adding a new
bank's layout means writing one class and appending it to the table (brief §10).

Normalized sign convention everywhere downstream: negative = money out of the
account — parsers translate each institution's printed convention into this.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ParsedTxn:
    posted_date: dt.date
    description: str
    amount_minor: int                      # normalized: negative = outflow
    transaction_date: dt.date | None = None
    external_id: str | None = None


@dataclass
class AccountHint:
    """What the document says about which account it belongs to."""

    institution: str | None = None
    mask: str | None = None                # last 4 digits
    account_type: str | None = None        # values from app.models.ledger.ACCOUNT_TYPES
    display_name: str | None = None


@dataclass
class ParseProblem:
    """A specific, recoverable description of something that didn't parse."""

    page: int | None
    line: str
    reason: str


@dataclass
class ParsedStatement:
    kind: str                              # pdf_statement | csv_export | ofx
    account: AccountHint
    transactions: list[ParsedTxn]
    period_start: dt.date | None = None
    period_end: dt.date | None = None
    opening_balance_minor: int | None = None   # internal sign (cards: -owed)
    closing_balance_minor: int | None = None
    problems: list[ParseProblem] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.transactions and not self.problems:
            return "parsed"
        if self.transactions:
            return "partial"
        return "failed"


class ParseError(Exception):
    """Unrecoverable parse failure with a user-actionable message."""

    def __init__(self, message: str, page: int | None = None):
        super().__init__(message)
        self.message = message
        self.page = page


class StatementParser(Protocol):
    """A parser for one document format/institution layout."""

    name: str
    kind: str

    def matches(self, filename: str, head: bytes) -> bool:
        """Cheap detection: can this parser read this file?"""
        ...

    def parse(self, filename: str, content: bytes) -> ParsedStatement:
        ...


def money_to_minor(text: str) -> int:
    """'-1,234.56' / '$1,234.56' / '- $24.50' → integer minor units."""
    cleaned = text.replace("$", "").replace(",", "").replace(" ", "")
    negative = cleaned.startswith("-")
    cleaned = cleaned.lstrip("+-")
    whole, _, frac = cleaned.partition(".")
    frac = (frac + "00")[:2]
    value = int(whole or 0) * 100 + int(frac or 0)
    return -value if negative else value


# Populated in app/parsers/__init__.py to avoid import cycles.
PARSERS: list[StatementParser] = []


def detect_parser(filename: str, head: bytes) -> StatementParser | None:
    for parser in PARSERS:
        if parser.matches(filename, head):
            return parser
    return None
