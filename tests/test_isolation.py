"""Non-negotiable #1: profile isolation is absolute.

Seeds profile B with data in every user-owned table, signs in as profile A, and
asserts every list endpoint returns zero of B's rows — then signs in as B and
asserts the same data IS visible to its owner (so a broken always-empty endpoint
cannot pass this test).
"""
from __future__ import annotations

import datetime as dt

A = {"display_name": "Alpha", "email": "alpha@example.com", "password": "alpha-pass-123"}
B = {"display_name": "Bravo", "email": "bravo@example.com", "password": "bravo-pass-123"}

LIST_ENDPOINTS = [
    "/api/institutions",
    "/api/accounts",
    "/api/transactions",
    "/api/categories",
    "/api/documents",
    "/api/budgets",
]


async def _seed_user_b_data(db_session, user_b_id: int) -> None:
    from app.models import (
        Account,
        AuditLog,
        Budget,
        Category,
        Document,
        Institution,
        Transaction,
    )

    inst = Institution(user_id=user_b_id, name="Bravo Bank", kind="bank")
    db_session.add(inst)
    await db_session.flush()

    acct = Account(
        user_id=user_b_id, institution_id=inst.id, display_name="Bravo Checking",
        mask="9999", type="checking", is_liquid=True,
    )
    db_session.add(acct)
    await db_session.flush()

    cat = Category(user_id=user_b_id, name="Bravo Secret Category", is_system=False)
    db_session.add(cat)
    await db_session.flush()

    db_session.add(Transaction(
        user_id=user_b_id, account_id=acct.id, posted_date=dt.date(2026, 1, 15),
        description_raw="BRAVO PRIVATE PURCHASE", amount_minor=-4200, type="debit",
        source="manual", dedupe_hash="b" * 64, category_id=cat.id,
    ))
    db_session.add(Document(
        user_id=user_b_id, account_id=acct.id, kind="pdf_statement",
        filename="bravo-jan.pdf", stored_path=f"data/{user_b_id}/documents/bravo-jan.pdf",
        sha256="b" * 64, parse_status="parsed",
    ))
    db_session.add(Budget(
        user_id=user_b_id, category_id=cat.id, period_type="monthly",
        period_start=dt.date(2026, 1, 1), target_minor=50000,
    ))
    db_session.add(AuditLog(user_id=user_b_id, event="test.seed"))
    await db_session.commit()


async def test_profile_a_sees_zero_of_profile_b(client, db_session):
    resp_b = await client.post("/api/auth/register", json=B)
    assert resp_b.status_code == 201
    user_b_id = resp_b.json()["id"]
    client.cookies.clear()

    await _seed_user_b_data(db_session, user_b_id)

    # Profile B sees its own data — proves the seeded rows are really served.
    resp = await client.post("/api/auth/login", json={"email": B["email"], "password": B["password"]})
    assert resp.status_code == 200
    for path in LIST_ENDPOINTS:
        items = (await client.get(path)).json()
        assert len(items) > 0, f"{path}: owner should see seeded rows"
    client.cookies.clear()

    # Profile A sees none of it. (System categories are shared by design; the
    # assertion for /api/categories is therefore "system rows only, and never
    # B's private category".)
    resp = await client.post("/api/auth/register", json=A)
    assert resp.status_code == 201
    for path in LIST_ENDPOINTS:
        resp = await client.get(path)
        assert resp.status_code == 200, path
        items = resp.json()
        if path == "/api/categories":
            assert all(c["is_system"] for c in items), \
                f"profile A must see only system categories, got {items!r}"
            assert all(c["name"] != "Bravo Secret Category" for c in items)
        else:
            assert items == [], f"{path}: profile A must see zero rows, got {items!r}"


async def test_transaction_filters_stay_scoped(client, db_session):
    """Filter parameters must never widen visibility across profiles."""
    resp_b = await client.post("/api/auth/register", json=B)
    user_b_id = resp_b.json()["id"]
    client.cookies.clear()
    await _seed_user_b_data(db_session, user_b_id)

    await client.post("/api/auth/register", json=A)
    resp = await client.get(
        "/api/transactions",
        params={"date_from": "2026-01-01", "date_to": "2026-12-31", "limit": 500},
    )
    assert resp.status_code == 200
    assert resp.json() == []
