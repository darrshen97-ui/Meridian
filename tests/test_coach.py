"""Milestone 11 checkpoint: coach answers are grounded in real queries, show
their sources, respect the 4-call cap, and degrade honestly."""
from __future__ import annotations

import json

import pytest

from app.providers.llm.base import LLMResponse, LLMUnavailable

JORDAN = {"display_name": "Jordan Reyes", "email": "jordan@meridian.demo",
          "password": "rowhouse-ledger-26"}
PRIYA = {"display_name": "Priya Raman", "email": "priya@meridian.demo",
         "password": "lakefront-audit-26"}


class ScriptedCoachLLM:
    """Plays a fixed sequence of decisions, echoing tool results it saw."""

    key = "fake"
    sends_data_off_device = False
    model = "fake-coach"

    def __init__(self, script: list[dict]):
        self.script = list(script)
        self.prompts: list[str] = []

    async def status(self):
        return {"provider": self.key, "endpoint": "http://127.0.0.1:1",
                "endpoint_is_local": True, "reachable": True, "model_present": True,
                "model": self.model, "models": []}

    async def complete_json(self, *, system, user, schema):
        self.prompts.append(user)
        decision = self.script.pop(0) if self.script else \
            {"action": "answer", "answer": "Done."}
        return LLMResponse(parsed=decision, model=self.model,
                           input_tokens=50, output_tokens=20, latency_ms=5)


def _install(monkeypatch, provider):
    import app.providers.llm as llm_module

    monkeypatch.setattr(llm_module, "_provider", provider)
    return provider


async def _synced(client, who):
    assert (await client.post("/api/auth/register", json=who)).status_code == 201
    assert (await client.post("/api/sync")).status_code == 200


async def test_grounded_answer_with_sources(client, monkeypatch):
    await _synced(client, JORDAN)
    fake = _install(monkeypatch, ScriptedCoachLLM([
        {"action": "call_tool", "tool": "get_spending_summary",
         "arguments": {"group_by": "month", "date_from": "2026-03-01",
                       "date_to": "2026-03-31"}},
        {"action": "call_tool", "tool": "query_transactions",
         "arguments": {"date_from": "2026-03-01", "date_to": "2026-03-31",
                       "merchant": "DENVER", "limit": 10}},
        {"action": "answer",
         "answer": "You spent heavily in March, largely the Denver trip."},
    ]))
    resp = await client.post("/api/coach/ask",
                             json={"question": "Why was March expensive?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert "Denver" in body["answer"]
    assert [c["tool"] for c in body["tool_calls"]] == \
        ["get_spending_summary", "query_transactions"]
    # The transactions the coach looked at are surfaced for verification.
    assert body["transactions"]
    assert all("DENVER" in t["description"].upper()
               or "DEN" in t["description"].upper() for t in body["transactions"])
    # The tool results genuinely entered the model's context.
    assert "TOTAL" in fake.prompts[1] or "total_spent" in fake.prompts[1]
    # The model was never handed a user id to manipulate.
    assert "user_id" not in fake.prompts[0]


async def test_tool_results_are_scoped_to_the_asking_user(client, monkeypatch):
    """Priya's coach must see zero of Jordan's data even with a greedy query."""
    await _synced(client, JORDAN)
    client.cookies.clear()
    await _synced(client, PRIYA)

    fake = _install(monkeypatch, ScriptedCoachLLM([
        {"action": "call_tool", "tool": "query_transactions",
         "arguments": {"date_from": "2025-08-01", "date_to": "2026-08-09",
                       "merchant": "SAFEWAY", "limit": 20}},
        {"action": "answer", "answer": "No Safeway transactions found."},
    ]))
    resp = await client.post("/api/coach/ask",
                             json={"question": "How much at Safeway?"})
    body = resp.json()
    assert body["transactions"] == []          # Jordan's grocer, not Priya's
    assert '"count": 0' in fake.prompts[1]


async def test_tool_loop_is_capped_at_four_calls(client, monkeypatch):
    await _synced(client, JORDAN)
    greedy = _install(monkeypatch, ScriptedCoachLLM([
        {"action": "call_tool", "tool": "query_transactions",
         "arguments": {"date_from": f"2026-{m:02d}-01", "date_to": f"2026-{m:02d}-28"}}
        for m in range(1, 11)
    ] + [{"action": "answer", "answer": "unreachable"}]))
    resp = await client.post("/api/coach/ask", json={"question": "Everything?"})
    body = resp.json()
    assert len(body["tool_calls"]) == 4
    # The forced-answer prompt told the model to stop and summarize.
    assert "Answer NOW" in greedy.prompts[-1]


async def test_no_query_means_no_guess(client, monkeypatch):
    await _synced(client, JORDAN)
    _install(monkeypatch, ScriptedCoachLLM([
        {"action": "answer", "answer": "You spend about $500 on dining."},
    ]))
    body = (await client.post("/api/coach/ask",
                              json={"question": "Dining spend?"})).json()
    assert "won't guess" in body["answer"]
    assert body["tool_calls"] == []


async def test_unknown_tool_is_corrected_not_fatal(client, monkeypatch):
    await _synced(client, JORDAN)
    fake = _install(monkeypatch, ScriptedCoachLLM([
        {"action": "call_tool", "tool": "read_bank_password", "arguments": {}},
        {"action": "call_tool", "tool": "get_account_balances", "arguments": {}},
        {"action": "answer", "answer": "Here are your balances."},
    ]))
    body = (await client.post("/api/coach/ask",
                              json={"question": "Balances?"})).json()
    assert body["available"] is True
    assert [c["tool"] for c in body["tool_calls"]] == ["get_account_balances"]
    assert "does not exist" in fake.prompts[1]


async def test_degrades_honestly_without_model(client, monkeypatch):
    class Down:
        key = "ollama"
        sends_data_off_device = False
        model = "qwen2.5:7b-instruct"

        async def status(self):
            return {}

        async def complete_json(self, **kwargs):
            raise LLMUnavailable(
                "Ollama isn't running on this machine. Install it and run "
                "`ollama pull qwen2.5:7b-instruct` to enable AI features.")

    await _synced(client, JORDAN)
    _install(monkeypatch, Down())
    resp = await client.post("/api/coach/ask", json={"question": "Am I okay?"})
    assert resp.status_code == 200          # degraded, not broken
    body = resp.json()
    assert body["available"] is False
    assert "ollama pull" in body["message"]
