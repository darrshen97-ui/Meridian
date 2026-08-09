"""Milestone 8 checkpoint: dashboard aggregates and inline category editing."""
from __future__ import annotations

JORDAN = {"display_name": "Jordan Reyes", "email": "jordan@meridian.demo",
          "password": "rowhouse-ledger-26"}


async def _synced_jordan(client) -> None:
    assert (await client.post("/api/auth/register", json=JORDAN)).status_code == 201
    assert (await client.post("/api/sync")).status_code == 200


async def test_dashboard_spending_power_math(client):
    await _synced_jordan(client)
    d = (await client.get("/api/dashboard")).json()

    # Spending power = liquid − card obligations, computed from the same payload.
    liquid_sum = sum(a["current_minor"] or 0 for a in d["liquid_accounts"])
    card_sum = sum(c["owed_minor"] for c in d["card_balances"])
    assert d["liquid_minor"] == liquid_sum
    assert d["obligations_minor"] == card_sum
    assert d["spending_power_minor"] == liquid_sum - card_sum

    # Liquid capital only: no crypto, loan, or investment accounts in the list.
    accounts = {a["id"]: a for a in (await client.get("/api/accounts")).json()}
    for entry in d["liquid_accounts"]:
        assert accounts[entry["account_id"]]["is_liquid"] is True
        assert accounts[entry["account_id"]]["type"] in (
            "checking", "savings", "payment_app")
    # The closed checking account is out of the liquid list.
    closed_ids = {a["id"] for a in accounts.values() if a["closed_at"]}
    assert closed_ids
    assert not closed_ids & {e["account_id"] for e in d["liquid_accounts"]}

    assert d["this_month"]["spent_minor"] > 0
    assert d["last_month"]["spent_minor"] > 0
    assert d["needs_attention"]["review_count"] > 0   # nothing categorized before M9
    assert len(d["recent"]) == 10


async def test_category_override_teaches_the_rules(client):
    await _synced_jordan(client)
    categories = {c["name"]: c["id"] for c in (await client.get("/api/categories")).json()}
    rows = (await client.get("/api/transactions",
                             params={"q": "SQ *BLUE STEM", "limit": 5})).json()
    assert rows, "expected ambiguous merchant rows to exist"
    target = rows[0]

    resp = await client.patch(f"/api/transactions/{target['id']}/category",
                              json={"category_id": categories["Dining"]})
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["category_id"] == categories["Dining"]
    assert updated["category_source"] == "user"
    assert updated["reviewed_at"] is not None

    # The override was persisted and recorded as a tier-1 correction.
    from app.core.db import get_session_factory
    from sqlalchemy import select
    from app.models import AuditLog, UserCorrection

    async with get_session_factory()() as s:
        corrections = (await s.scalars(select(UserCorrection))).all()
        assert len(corrections) == 1
        assert "BLUE STEM" in corrections[0].merchant_pattern
        events = set(await s.scalars(select(AuditLog.event)))
        assert "category.overridden" in events


async def test_category_filters_and_search_are_scoped(client):
    await _synced_jordan(client)
    rows = (await client.get("/api/transactions",
                             params={"q": "STREAMMAX", "limit": 50})).json()
    assert rows and all("STREAMMAX" in r["description_raw"] for r in rows)

    rows = (await client.get("/api/transactions",
                             params={"source": "provider", "limit": 5})).json()
    assert rows and all(r["external_id"] for r in rows)

    resp = await client.patch("/api/transactions/999999/category",
                              json={"category_id": 1})
    assert resp.status_code == 404
