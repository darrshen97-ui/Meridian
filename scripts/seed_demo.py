"""Seed the two demo profiles: provider sync, statements, reconciliation, budgets.

The demo profiles exist so a new user has somewhere to look before they have any
data of their own, which means a profile with empty Documents, Reconciliation and
Budgets screens is a half-finished demo. This script imports the bundled sample
statements for both profiles, reconciles every period they produce, and sets
budget targets, so every screen has something true on it.

Idempotent: profiles that already exist are left alone. The Dockerfile runs this at
image build time and `serve.py` copies the result into place; the launcher runs it
on first start. Also useful in development:

    python scripts/seed_demo.py            # everything
    python scripts/seed_demo.py --minimal  # provider sync only (seconds, not minutes)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from app.core.demo import DEMO_CREDENTIALS  # noqa: E402  (needs ROOT on the path)

# (display name, profile key) per demo email; the passwords live in app/core/demo.py
# because the sign-in screen offers them too.
DEMO_PROFILES = [
    ("Jordan Reyes", "jordan@meridian.demo", "jordan"),
    ("Priya Raman", "priya@meridian.demo", "priya"),
]

DOCUMENT_SUFFIXES = (".pdf", ".csv", ".ofx")

# Monthly targets, in cents, set against each profile's own median monthly spending
# in that category. Most sit a little above it; Dining and Shopping sit below, so the
# Budgets screen shows overspend as well as headroom rather than a wall of green.
BUDGETS = {
    "jordan": {"Groceries": 95_000, "Dining": 125_000, "Transport": 40_000,
               "Subscriptions": 15_000, "Shopping": 150_000, "Travel": 150_000},
    "priya": {"Groceries": 75_000, "Dining": 75_000, "Transport": 12_000,
              "Subscriptions": 12_000, "Shopping": 100_000, "Utilities": 30_000},
}

# Targets are per calendar month; cover the statement period and beyond, so the
# Budgets screen is populated whenever the demo happens to be opened.
BUDGET_MONTHS = [(y, m) for y in (2025, 2026, 2027) for m in range(1, 13)
                 if (y, m) >= (2025, 8)]


async def import_documents(session, user_id: int, profile_key: str) -> tuple[int, int]:
    """Upload and import every bundled statement for this profile."""
    from app.services.ingestion import IngestionError, IngestionService

    folder = ROOT / "sample_data" / profile_key
    paths = sorted(p for p in folder.rglob("*")
                   if p.is_file() and p.suffix.lower() in DOCUMENT_SUFFIXES)
    service = IngestionService(session)
    imported = rows = 0
    for path in paths:
        try:
            doc = await service.upload(user_id, path.name, path.read_bytes())
            result = await service.import_document(user_id, doc.id, create_account=True)
        except IngestionError as exc:
            print(f"    ! {path.name}: {exc}")
            continue
        imported += 1
        rows += result.imported
    return imported, rows


def ground_truth_categories(profile_key: str) -> dict[str, str]:
    """Merchant → category, from the generator that produced the dataset.

    The demo profiles are meant to show what the app looks like in use, and in use
    a ledger is categorized. The deliberately cryptic descriptors are left out: they
    exist to populate the review queue and to give the model something real to do,
    so pre-filling them would delete the feature they were built to demonstrate.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    from mockgen import jordan as jordan_gen
    from mockgen.output import build_ledgers

    led = dict(zip(("jordan", "priya"), build_ledgers()))[profile_key]
    seen: dict[str, set[str]] = {}
    for t in led.txns:
        if t.description in jordan_gen.AMBIGUOUS or t.category in ("", "Uncategorized"):
            continue
        seen.setdefault(t.description, set()).add(t.category)
    # A descriptor that means two different things is not ground truth.
    return {d: next(iter(c)) for d, c in seen.items() if len(c) == 1}


async def categorize(session, user_id: int, profile_key: str) -> tuple[int, int, int]:
    """Deterministic rules first, then the generator's ground truth for the rest."""
    from sqlalchemy import func, select

    from app.models import Transaction
    from app.services.categorization import CategorizationService
    from app.services.ledger import LedgerService

    service = CategorizationService(session)
    by_rules = 0
    while True:  # run() works in batches; rows rules can't place are left alone
        summary = await service.run(user_id, limit=500)
        by_rules += summary["rules_applied"]
        if summary["rules_applied"] == 0:
            break

    truth = ground_truth_categories(profile_key)
    categories = {c.name: c.id
                  for c in await LedgerService(session).list_categories(user_id)}
    rows = list(await session.scalars(
        select(Transaction).where(Transaction.user_id == user_id,
                                  Transaction.category_id.is_(None))))
    by_truth = 0
    for row in rows:
        name = truth.get(row.description_raw)
        if name is None:  # statements truncate long descriptors
            name = next((v for k, v in truth.items()
                         if k.startswith(row.description_raw)), None)
        if name is None or name not in categories:
            continue
        row.category_id = categories[name]
        row.category_source = "demo"
        row.category_confidence = 1.0
        by_truth += 1
    await session.commit()

    left = await session.scalar(
        select(func.count()).select_from(Transaction).where(
            Transaction.user_id == user_id, Transaction.category_id.is_(None)))
    return by_rules, by_truth, left


async def reconcile_everything(session, user_id: int) -> tuple[int, int]:
    from app.services.reconciliation import ReconciliationService

    runs = await ReconciliationService(session).run_all(user_id)
    findings = sum(len([f for f in r["findings"] if not f["resolved"]]) for r in runs)
    return len(runs), findings


async def set_budgets(session, user_id: int, profile_key: str) -> int:
    from app.services.budgets import BudgetService
    from app.services.ledger import LedgerService

    categories = {c.name: c.id
                  for c in await LedgerService(session).list_categories(user_id)}
    service = BudgetService(session)
    count = 0
    for name, target in BUDGETS[profile_key].items():
        category_id = categories.get(name)
        if category_id is None:
            continue
        for (year, month) in BUDGET_MONTHS:
            await service.set_target(user_id, category_id, target, f"{year}-{month:02d}")
            count += 1
    return count


async def main(minimal: bool) -> None:
    import os

    # Seeding shouldn't sit through simulated provider latency or hiccups.
    os.environ.setdefault("MOCK_MIN_LATENCY", "0")
    os.environ.setdefault("MOCK_MAX_LATENCY", "0")
    os.environ.setdefault("MOCK_FAILURE_RATE", "0")

    from app.core.db import get_session_factory
    from app.services.auth import AuthError, AuthService
    from app.services.sync import SyncService

    async with get_session_factory()() as session:
        auth = AuthService(session)
        for display_name, email, profile_key in DEMO_PROFILES:
            try:
                profile = await auth.register(display_name, email,
                                              DEMO_CREDENTIALS[email])
                created = True
            except AuthError:
                found = await auth.users.get_by_email_with_hash(email)
                profile = found[0] if found else None
                created = False
            if profile is None:
                print(f"  ! could not create or find {email}")
                continue
            if not created:
                print(f"  {display_name} already exists — skipped")
                continue

            started = time.monotonic()
            summary = await SyncService(session).sync(profile.id, email)
            print(f"  seeded {display_name}: {summary['new_transactions']} "
                  f"transactions ({summary['status']})", flush=True)
            if minimal:
                continue

            docs, rows = await import_documents(session, profile.id, profile_key)
            print(f"    imported {docs} documents, {rows} new rows "
                  f"(the rest matched what the provider already had)", flush=True)
            by_rules, by_truth, left = await categorize(session, profile.id, profile_key)
            print(f"    categorized {by_rules} by rule and {by_truth} from the "
                  f"dataset's ground truth; {left} left for the review queue",
                  flush=True)
            runs, findings = await reconcile_everything(session, profile.id)
            print(f"    reconciled {runs} periods, {findings} findings to look at",
                  flush=True)
            targets = await set_budgets(session, profile.id, profile_key)
            print(f"    set {targets} monthly budget targets "
                  f"({time.monotonic() - started:.0f}s)", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minimal", action="store_true",
                        help="provider sync only — skip statements, reconciliation "
                             "and budgets")
    asyncio.run(main(parser.parse_args().minimal))
