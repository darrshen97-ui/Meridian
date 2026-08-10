"""Milestone 12 checkpoint: budget targets vs actuals, and projections that
demonstrably use the real historical spending distribution."""
from __future__ import annotations

import datetime as dt

import pytest

from app.providers.llm.base import LLMResponse

JORDAN = {"display_name": "Jordan Reyes", "email": "jordan@meridian.demo",
          "password": "rowhouse-ledger-26"}
PRIYA = {"display_name": "Priya Raman", "email": "priya@meridian.demo",
         "password": "lakefront-audit-26"}


class ExplainerLLM:
    key = "fake"
    sends_data_off_device = False
    model = "fake-explainer"

    def __init__(self):
        self.prompts: list[str] = []

    async def status(self):
        return {"provider": self.key, "endpoint": "http://127.0.0.1:1",
                "endpoint_is_local": True, "reachable": True, "model_present": True,
                "model": self.model, "models": []}

    async def complete_json(self, *, system, user, schema):
        self.prompts.append(user)
        return LLMResponse(parsed={
            "explanation": "Cutting groceries frees a steady amount each month.",
            "watch_out_for": "Grocery cuts often shift spending into dining.",
        }, model=self.model, input_tokens=50, output_tokens=30, latency_ms=4)


async def _prepared_jordan(client):
    """Register, sync, and categorize deterministically (rules pass only)."""
    assert (await client.post("/api/auth/register", json=JORDAN)).status_code == 201
    assert (await client.post("/api/sync")).status_code == 200
    # The model endpoint is a closed port in tests → only the rules pass runs,
    # which deterministically categorizes groceries, income, transfers, etc.
    resp = await client.post("/api/categorize/run", json={"limit": 5000})
    assert resp.json()["rules_applied"] > 100


async def test_budget_targets_and_actuals(client):
    await _prepared_jordan(client)
    categories = {c["name"]: c["id"] for c in (await client.get("/api/categories")).json()}

    resp = await client.put(f"/api/budgets/{categories['Groceries']}",
                            json={"target_minor": 40000, "period": "2026-07"})
    assert resp.status_code == 200

    overview = (await client.get("/api/budgets/overview",
                                 params={"period": "2026-07"})).json()
    groceries = next(e for e in overview["entries"] if e["category"] == "Groceries")
    assert groceries["target_minor"] == 40000
    assert groceries["actual_minor"] > 0

    # The actual matches a direct sum over the ledger for that month.
    rows = (await client.get("/api/transactions", params={
        "category_id": categories["Groceries"], "date_from": "2026-07-01",
        "date_to": "2026-07-31", "limit": 500})).json()
    manual = sum(-r["amount_minor"] for r in rows if r["amount_minor"] < 0)
    assert groceries["actual_minor"] == manual
    assert groceries["over_minor"] == max(0, manual - 40000)

    # Clearing works; clearing twice is a specific 404.
    assert (await client.delete(f"/api/budgets/{categories['Groceries']}")).status_code == 204
    assert (await client.delete(f"/api/budgets/{categories['Groceries']}")).status_code == 404


async def test_simulation_uses_real_distribution(client, monkeypatch):
    await _prepared_jordan(client)
    import app.providers.llm as llm_module

    fake = ExplainerLLM()
    monkeypatch.setattr(llm_module, "_provider", fake)

    categories = {c["name"]: c["id"] for c in (await client.get("/api/categories")).json()}
    resp = await client.post("/api/simulate", json={
        "adjustments": [{"category_id": categories["Groceries"],
                         "percent_change": -30}],
        "months_ahead": 6, "lookback_months": 6})
    assert resp.status_code == 200
    sim = resp.json()

    # The baseline is the real mean over complete months — recompute it manually.
    n = sim["lookback_complete_months"]
    assert n >= 5
    today = dt.date.today().replace(day=1)
    total = 0
    for back in range(1, n + 1):
        month = today.month - back
        year = today.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        first = dt.date(year, month, 1)
        last = (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1) \
            - dt.timedelta(days=1)
        rows = (await client.get("/api/transactions", params={
            "category_id": categories["Groceries"],
            "date_from": first.isoformat(), "date_to": last.isoformat(),
            "limit": 500})).json()
        total += sum(-r["amount_minor"] for r in rows if r["amount_minor"] < 0)
    (adj,) = sim["adjustments"]
    assert adj["monthly_mean_minor"] == total // n
    assert adj["monthly_min_minor"] <= adj["monthly_mean_minor"] <= adj["monthly_max_minor"]

    # Deterministic projection arithmetic, straight from the distribution.
    expected_delta = adj["monthly_mean_minor"] - round(adj["monthly_mean_minor"] * 0.7)
    assert sim["monthly_delta_minor"] == expected_delta
    assert len(sim["projection"]) == 6
    for m, row in enumerate(sim["projection"], start=1):
        assert row["cumulative_delta_minor"] == m * expected_delta
        assert row["adjusted_power_minor"] - row["baseline_power_minor"] == \
            m * expected_delta

    # The model explained (language), and its facts came from the math.
    assert sim["model_explanation"]
    assert sim["watch_out_for"]
    assert "Groceries -30%" in fake.prompts[-1]
    assert sim["summary"].startswith("Over the last")


async def test_simulation_degrades_and_refuses_empty_history(client):
    await _prepared_jordan(client)
    categories = {c["name"]: c["id"] for c in (await client.get("/api/categories")).json()}

    # Degraded: model endpoint is closed in tests → numbers still complete.
    resp = await client.post("/api/simulate", json={
        "adjustments": [{"category_id": categories["Groceries"],
                         "percent_change": -30}]})
    sim = resp.json()
    assert sim["model_explanation"] is None
    assert sim["summary"] and sim["projection"]

    # A category with no categorized history refuses honestly.
    resp = await client.post("/api/simulate", json={
        "adjustments": [{"category_id": categories["Education"],
                         "percent_change": -30}]})
    assert resp.status_code == 409
    assert "No categorized spending history" in resp.json()["detail"]


async def test_budgets_are_isolated_between_profiles(client):
    await _prepared_jordan(client)
    categories = {c["name"]: c["id"] for c in (await client.get("/api/categories")).json()}
    await client.put(f"/api/budgets/{categories['Groceries']}",
                     json={"target_minor": 40000})
    client.cookies.clear()

    assert (await client.post("/api/auth/register", json=PRIYA)).status_code == 201
    overview = (await client.get("/api/budgets/overview")).json()
    assert all(e["target_minor"] is None for e in overview["entries"])
