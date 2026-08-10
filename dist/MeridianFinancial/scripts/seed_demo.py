"""Seed the two demo profiles and run their initial provider sync.

Idempotent: profiles that already exist are left alone. The launcher runs this
on first start (milestone 14); it's also handy in development:

    python scripts/seed_demo.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DEMO_PROFILES = [
    ("Jordan Reyes", "jordan@meridian.demo", "rowhouse-ledger-26"),
    ("Priya Raman", "priya@meridian.demo", "lakefront-audit-26"),
]


async def main() -> None:
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
        for display_name, email, password in DEMO_PROFILES:
            try:
                profile = await auth.register(display_name, email, password)
                created = True
            except AuthError:
                found = await auth.users.get_by_email_with_hash(email)
                profile = found[0] if found else None
                created = False
            if profile is None:
                print(f"  ! could not create or find {email}")
                continue
            if created:
                summary = await SyncService(session).sync(profile.id, email)
                print(f"  seeded {display_name}: "
                      f"{summary['new_transactions']} transactions "
                      f"({summary['status']})")
            else:
                print(f"  {display_name} already exists — skipped")


if __name__ == "__main__":
    asyncio.run(main())
