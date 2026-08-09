"""Milestone 6 checkpoint: provider layer, incremental sync, retry, SSE events."""
from __future__ import annotations

from pathlib import Path

import pytest

SAMPLE = Path(__file__).parent.parent / "sample_data"
JORDAN = {"display_name": "Jordan Reyes", "email": "jordan@meridian.demo",
          "password": "rowhouse-ledger-26"}
CHASE_PDF = SAMPLE / "jordan" / "statements" / "chase" / "checking_7734_2025-09.pdf"

# The provider feed carries every ledger row except the one statement-only
# planted event (missing_in_provider), including the pending row and the tail.
JORDAN_PROVIDER_COUNT = 2277


async def _register_jordan(client):
    resp = await client.post("/api/auth/register", json=JORDAN)
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_full_sync_then_incremental(client):
    await _register_jordan(client)

    resp = await client.post("/api/sync")
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["status"] == "succeeded"
    assert summary["new_transactions"] == JORDAN_PROVIDER_COUNT
    assert len(summary["accounts"]) == 11
    assert all(a["status"] == "ok" for a in summary["accounts"])

    accounts = (await client.get("/api/accounts")).json()
    assert len(accounts) == 11
    closed = [a for a in accounts if a["closed_at"]]
    assert {a["mask"] for a in closed if a["mask"]} == {"8123", "5561"}

    institutions = (await client.get("/api/institutions")).json()
    assert len(institutions) == 7

    balances = (await client.get("/api/balances")).json()
    assert len(balances) == 11
    assert all(isinstance(b["current_minor"], int) for b in balances)

    # Incremental: the cursor advanced, so a second sync ingests nothing.
    resp = await client.post("/api/sync")
    assert resp.json()["new_transactions"] == 0

    status = (await client.get("/api/sync/status")).json()
    assert status["last_run"]["status"] == "succeeded"
    assert status["last_run"]["finished_at"] is not None


async def test_simulated_transactions_flow_through_sse(client):
    user_id = await _register_jordan(client)
    await client.post("/api/sync")

    from app.services.events import get_event_bus

    bus = get_event_bus()
    queue = bus.subscribe(user_id)

    resp = await client.post("/api/dev/simulate-transactions", json={"count": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["injected"] == 3
    assert body["sync"]["new_transactions"] == 3

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    types = [e[0] for e in events]
    assert "sync.started" in types
    assert "sync.completed" in types
    assert ("transactions.new", {"count": 3}) in events
    bus.unsubscribe(user_id, queue)


async def test_sync_retries_through_forced_failures(client, monkeypatch):
    """A provider that fails half its calls must still complete a sync."""
    from app.providers import financial as fin
    from app.providers.financial.mock import MockProvider

    chaotic = MockProvider(SAMPLE / "provider_fixtures", min_latency=0, max_latency=0,
                           failure_rate=0.5, rate_limit_every=3)
    monkeypatch.setattr(fin, "_provider", chaotic)

    async def instant_sleep(_seconds):  # keep the backoff logic, skip the waiting
        return None

    import app.services.sync as sync_module
    monkeypatch.setattr(sync_module.asyncio, "sleep", instant_sleep)

    await _register_jordan(client)
    total = 0
    for _round in range(20):
        resp = await client.post("/api/sync")
        if resp.status_code != 200:      # whole run failed; state was recorded
            status = (await client.get("/api/sync/status")).json()
            assert status["last_run"]["status"] == "failed"
            assert status["last_run"]["error"]
            continue
        body = resp.json()
        assert body["status"] in ("succeeded", "partial")
        total += body["new_transactions"]
        if body["status"] == "succeeded" and total == JORDAN_PROVIDER_COUNT:
            break
    # Retry + cursor resume must reach a complete ledger despite 50% failures,
    # and never ingest a row twice.
    assert total == JORDAN_PROVIDER_COUNT
    from app.core.db import get_session_factory
    from sqlalchemy import func, select
    from app.models import Transaction

    async with get_session_factory()() as s:
        db_count = await s.scalar(select(func.count(Transaction.id)))
    assert db_count == JORDAN_PROVIDER_COUNT


async def test_statement_rows_gain_provider_identity_on_sync(client):
    """Import a PDF first, then sync: rows merge, gaining external ids — no dupes."""
    await _register_jordan(client)

    with open(CHASE_PDF, "rb") as f:
        resp = await client.post("/api/documents/upload",
                                 files=[("files", (CHASE_PDF.name, f, "application/pdf"))])
    doc_id = resp.json()[0]["document"]["id"]
    resp = await client.post(f"/api/documents/{doc_id}/import",
                             json={"create_account": True})
    imported = resp.json()["imported"]
    assert imported > 0

    resp = await client.post("/api/sync")
    assert resp.status_code == 200

    rows = (await client.get("/api/transactions", params={
        "date_from": "2025-09-01", "date_to": "2025-09-30", "limit": 500})).json()
    chase_rows = [r for r in rows if r["source"] == "statement"]
    assert len(chase_rows) == imported          # merged, not duplicated
    # (external_id isn't in the DTO shape; verify via DB that merges happened.)
    from app.core.db import get_session_factory
    from sqlalchemy import select, func
    from app.models import Transaction

    async with get_session_factory()() as s:
        dupes = await s.execute(
            select(Transaction.account_id, Transaction.dedupe_hash,
                   func.count(Transaction.id))
            .group_by(Transaction.account_id, Transaction.dedupe_hash)
            .having(func.count(Transaction.id) > 2))
        assert dupes.all() == []
        with_both = await s.scalar(
            select(func.count(Transaction.id)).where(
                Transaction.source_document_id.is_not(None),
                Transaction.external_id.is_not(None)))
        assert with_both == imported


async def test_pending_never_cleared_lands_pending(client):
    await _register_jordan(client)
    await client.post("/api/sync")
    from app.core.db import get_session_factory
    from sqlalchemy import select
    from app.models import Transaction

    async with get_session_factory()() as s:
        pending = (await s.scalars(
            select(Transaction).where(Transaction.pending.is_(True)))).all()
        assert len(pending) == 1
        assert "CONOCO" in pending[0].description_raw


async def test_plaid_stub_is_explicitly_unimplemented():
    from app.providers.financial.plaid import PlaidProvider

    with pytest.raises(NotImplementedError):
        await PlaidProvider().list_accounts("anyone")
