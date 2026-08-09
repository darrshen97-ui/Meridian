"""Transaction identity and cross-source matching.

The heart of reconciliation (brief §7): when statement and provider data describe
the same transaction, they collapse to one row with both sources recorded.

Two layers:
  1. Exact — dedupe_hash over (account, posted date, amount, normalized description),
     occurrence-aware so two genuinely identical purchases don't collapse into one.
  2. Fuzzy — same amount, dates within ±3 days, description token overlap ≥ 0.5,
     strict one-to-one greedy assignment (lowest date distance, then best overlap).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass

_PUNCT = re.compile(r"[^A-Z0-9*#& ]")
_SPACES = re.compile(r"\s+")

DATE_WINDOW_DAYS = 3
SIMILARITY_FLOOR = 0.5


def normalize_description(description: str) -> str:
    text = _PUNCT.sub(" ", description.upper())
    return _SPACES.sub(" ", text).strip()


def dedupe_hash(account_id: int, posted_date: dt.date, amount_minor: int,
                description: str) -> str:
    payload = f"{account_id}|{posted_date.isoformat()}|{amount_minor}|" \
              f"{normalize_description(description)}"
    return hashlib.sha256(payload.encode()).hexdigest()


def _tokens(description: str) -> set[str]:
    return {t for t in normalize_description(description).split(" ") if len(t) >= 2}


def similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


@dataclass(frozen=True)
class Incoming:
    """A parsed transaction on its way into an account's ledger."""

    index: int                 # caller's index into the parsed list
    posted_date: dt.date
    amount_minor: int
    description: str


@dataclass(frozen=True)
class Existing:
    """An already-persisted transaction, as the matcher needs to see it."""

    id: int
    posted_date: dt.date
    amount_minor: int
    description: str
    dedupe_hash: str


@dataclass
class MatchResult:
    to_insert: list[int]               # indexes of incoming rows that are new
    merged: dict[int, int]             # incoming index -> existing transaction id


def match_incoming(account_id: int, incoming: list[Incoming],
                   existing: list[Existing]) -> MatchResult:
    """Decide which incoming rows already exist in the account's ledger."""
    merged: dict[int, int] = {}
    taken: set[int] = set()

    # Layer 1 — exact hash, occurrence-aware.
    by_hash: dict[str, list[Existing]] = {}
    for e in existing:
        by_hash.setdefault(e.dedupe_hash, []).append(e)
    unmatched: list[Incoming] = []
    for inc in incoming:
        h = dedupe_hash(account_id, inc.posted_date, inc.amount_minor, inc.description)
        pool = [e for e in by_hash.get(h, []) if e.id not in taken]
        if pool:
            # Occurrence-aware: N identical existing rows absorb at most N
            # identical incoming rows; any extras insert as genuinely new.
            merged[inc.index] = pool[0].id
            taken.add(pool[0].id)
        else:
            unmatched.append(inc)

    # Layer 2 — shift/truncation tolerant, one-to-one by score.
    candidates: list[tuple[float, int, int, int]] = []
    for inc in unmatched:
        for e in existing:
            if e.id in taken or e.amount_minor != inc.amount_minor:
                continue
            delta = abs((e.posted_date - inc.posted_date).days)
            if delta > DATE_WINDOW_DAYS:
                continue
            sim = similarity(e.description, inc.description)
            if sim < SIMILARITY_FLOOR:
                continue
            candidates.append((delta + 2 * (1 - sim), delta, inc.index, e.id))
    matched_incoming: set[int] = set()
    for score, _delta, inc_index, existing_id in sorted(candidates):
        if inc_index in matched_incoming or existing_id in taken:
            continue
        merged[inc_index] = existing_id
        matched_incoming.add(inc_index)
        taken.add(existing_id)

    to_insert = [inc.index for inc in incoming if inc.index not in merged]
    return MatchResult(to_insert=to_insert, merged=merged)
