"""The seeded demo profiles and their published credentials.

These two profiles exist to give a first-time visitor something to look at, so
their passwords are not secrets: they are printed in the README, in the dataset
guide, and on the welcome screen itself. Keeping them in one place means the sign-in
screen can offer them without a second list drifting out of step with the seeder.

A profile someone creates themselves is never in here, and nothing about it is
exposed before sign-in.
"""
from __future__ import annotations

DEMO_CREDENTIALS: dict[str, str] = {
    "jordan@meridian.demo": "rowhouse-ledger-26",
    "priya@meridian.demo": "lakefront-audit-26",
}

DEMO_BLURBS: dict[str, str] = {
    "jordan@meridian.demo":
        "Twelve institutions, 117 imported statements, and a year of reconciliations "
        "with real findings in them — a duplicate charge, a card compromise, a "
        "subscription that crept up.",
    "priya@meridian.demo":
        "A second, entirely separate ledger. Nothing of Jordan's is reachable from "
        "here: different institutions, merchants and city, by construction.",
}
