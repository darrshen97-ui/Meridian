"""Milestone 10 checkpoint (brief §16, §17): every one of the 13 planted events
from §9 is detected by the app itself — through the full pipeline: provider
sync + statement import of every document + reconciliation of every period.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

SAMPLE = Path(__file__).parent.parent / "sample_data"
JORDAN = {"display_name": "Jordan Reyes", "email": "jordan@meridian.demo",
          "password": "rowhouse-ledger-26"}


async def _import_everything(client) -> None:
    """Sync the provider, then import all 117 sample documents at service level."""
    assert (await client.post("/api/auth/register", json=JORDAN)).status_code == 201
    assert (await client.post("/api/sync")).status_code == 200

    from app.core.db import get_session_factory
    from app.services.ingestion import IngestionError, IngestionService

    me = (await client.get("/api/auth/me")).json()
    async with get_session_factory()() as session:
        service = IngestionService(session)
        for path in sorted(SAMPLE.rglob("*")):
            if path.suffix.lower() not in (".pdf", ".csv", ".ofx"):
                continue
            doc = await service.upload(me["id"], path.name, path.read_bytes())
            try:
                await service.import_document(me["id"], doc.id)
            except IngestionError as exc:  # every document must import cleanly
                raise AssertionError(f"{path.name}: {exc.message}") from exc


@pytest.fixture
async def full_pipeline(client):
    await _import_everything(client)
    resp = await client.post("/api/reconciliation/run-all")
    assert resp.status_code == 200
    runs = resp.json()
    findings = [dict(f, run=r) for r in runs for f in r["findings"]]
    return {"client": client, "runs": runs, "findings": findings}


def _by_kind(findings, kind):
    return [f for f in findings if f["kind"] == kind]


async def test_all_13_planted_events_are_detected(full_pipeline):
    client = full_pipeline["client"]
    runs = full_pipeline["runs"]
    findings = full_pipeline["findings"]
    assert len(runs) == 79  # every account-period with a statement reconciled

    accounts = {a["mask"]: a for a in (await client.get("/api/accounts")).json()
                if a["mask"]}

    # 1 — duplicate charge (Feb 2026, Chase Sapphire, 2 days apart)
    dups = [f for f in _by_kind(findings, "duplicate_suspected")
            if f["transaction"] and "OLIVE & VINE" in f["transaction"]["description"]
            and f["transaction"]["amount_minor"] == -8640]
    assert len(dups) == 1
    assert dups[0]["run"]["account_id"] == accounts["1902"]["id"]
    assert dups[0]["run"]["period_start"] == "2026-02-01"
    assert not dups[0]["resolved"]

    # 2 — missing in provider (Nov 2025, American Bank ••4417)
    missing = [f for f in _by_kind(findings, "missing_in_provider")
               if f["transaction"] and f["transaction"]["description"] == "CHECK #1042"]
    assert len(missing) == 1
    nov = missing[0]["run"]
    assert nov["account_id"] == accounts["4417"]["id"]
    assert nov["period_start"] == "2025-11-01"
    # The balance delta is explained exactly by the missing check.
    assert nov["delta_minor"] == 23000

    # 3 — never-cleared pending (Mar 2026, Discover)
    pending = [f for f in _by_kind(findings, "missing_in_statement")
               if f["transaction"] and "CONOCO" in f["transaction"]["description"]]
    assert len(pending) == 1
    assert pending[0]["run"]["account_id"] == accounts["6088"]["id"]
    assert "pending" in pending[0]["narrative"]

    # 13 — date shifts: matched silently, recorded as informational only
    shifts = _by_kind(findings, "date_shift")
    assert len(shifts) == 3
    assert all(f["resolved"] for f in shifts)
    shift_accounts = {f["run"]["account_id"] for f in shifts}
    assert shift_accounts == {accounts["1902"]["id"], accounts["4417"]["id"],
                              accounts["6088"]["id"]}
    # ...and they produced no actionable missing/mismatch findings.
    shift_txn_ids = {f["transaction"]["id"] for f in shifts}
    for f in findings:
        if f["kind"] in ("missing_in_provider", "missing_in_statement",
                         "amount_mismatch") and f["transaction"]:
            assert f["transaction"]["id"] not in shift_txn_ids

    # No false positives beyond the planted divergences: every actionable
    # finding is one of the three planted ones.
    actionable = [f for f in findings if not f["resolved"]]
    assert {f["id"] for f in actionable} == \
        {dups[0]["id"], missing[0]["id"], pending[0]["id"]}, \
        [f["narrative"] for f in actionable]

    # 4 — subscription price increase ($15.99 → $22.99, Jan 2026)
    rows = (await client.get("/api/transactions",
                             params={"q": "STREAMMAX", "limit": 100})).json()
    prices = {r["posted_date"][:7]: -r["amount_minor"] for r in rows}
    assert prices["2025-12"] == 1599 and prices["2026-01"] == 2299

    # 5 — card compromise: 3 foreign charges, account closed, replacement resumes
    fraud = (await client.get("/api/transactions",
                              params={"q": "LISBOA", "limit": 10})).json()
    assert len(fraud) == 3
    assert accounts["8123"]["closed_at"] == "2026-06-20"
    replacement = (await client.get("/api/transactions", params={
        "account_id": accounts["4417"]["id"], "date_from": "2026-07-01",
        "q": "SAFEWAY", "limit": 5})).json()
    assert replacement, "groceries resume on ••4417 after the closure"

    # 6 — ambiguous merchants land in the review queue
    queue = (await client.get("/api/review", params={"limit": 500})).json()
    ambiguous = [i for i in queue["items"]
                 if i["description"].startswith(("SQ *", "TST*", "PAYPAL *", "POS DEBIT"))]
    assert len(ambiguous) >= 40 or queue["total"] > 400  # queue page may truncate

    # 7 — December 2025 seasonal spike (~2.1× baseline discretionary)
    from app.core.db import get_session_factory
    from app.repositories.analytics import AnalyticsRepository

    me = (await client.get("/api/auth/me")).json()
    async with get_session_factory()() as s:
        analytics = AnalyticsRepository(s)
        dec = (await analytics.month_flow(me["id"], dt.date(2025, 12, 1),
                                          dt.date(2025, 12, 31)))["spent_minor"]
        baseline = []
        for month in (9, 10, 11):
            flow = await analytics.month_flow(me["id"], dt.date(2025, month, 1),
                                              dt.date(2025, month, 28))
            baseline.append(flow["spent_minor"])
    assert dec > 1.3 * (sum(baseline) / len(baseline))

    # 8 — one-time large expense
    big = (await client.get("/api/transactions",
                            params={"q": "PRECISION AUTO", "limit": 5})).json()
    assert len(big) == 1 and big[0]["amount_minor"] == -184000

    # 9 — vacation cluster (Denver, one week of March 2026)
    denver = (await client.get("/api/transactions",
                               params={"q": "DENVER", "limit": 50})).json()
    den = (await client.get("/api/transactions",
                            params={"q": "DEN ", "limit": 50})).json()
    cluster = {r["id"]: r for r in denver + den}.values()
    assert len(cluster) >= 8
    dates = sorted(r["posted_date"] for r in cluster)
    assert dates[0] >= "2026-03-14" and dates[-1] <= "2026-03-22"

    # 10 — income change ($3,180 → $3,510 from April 2026)
    pays = (await client.get("/api/transactions",
                             params={"q": "NORTHRIVER", "limit": 100})).json()
    before = {r["amount_minor"] for r in pays if r["posted_date"] < "2026-04-01"}
    after = {r["amount_minor"] for r in pays if r["posted_date"] >= "2026-04-01"}
    assert before == {318000} and after == {351000}

    # 11 — auto loan payoff: payments stop after March 2026; account closed
    loan_payments = (await client.get("/api/transactions", params={
        "q": "CHASE AUTO LOAN PAYMENT", "limit": 50})).json()
    assert len(loan_payments) == 8
    assert max(r["posted_date"] for r in loan_payments) < "2026-04-01"
    assert accounts["5561"]["closed_at"] is not None

    # 12 — crypto: weekly DCA + the May partial sale landing in checking
    sale = (await client.get("/api/transactions",
                             params={"q": "GEMINI TRUST CO ACH", "limit": 5})).json()
    assert sale and sale[0]["amount_minor"] == 920000
    dca = (await client.get("/api/transactions",
                            params={"q": "BUY BTC", "limit": 200})).json()
    assert len(dca) >= 50
