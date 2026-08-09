"""Milestone 9 checkpoint: two-pass categorization, learning loop, review queue.

Uses a fake LLM provider behind the real protocol so the pipeline logic is
tested deterministically; the OllamaProvider itself is exercised separately
against a real local model where available.
"""
from __future__ import annotations

import json

import pytest

from app.providers.llm.base import LLMResponse, LLMUnavailable

JORDAN = {"display_name": "Jordan Reyes", "email": "jordan@meridian.demo",
          "password": "rowhouse-ledger-26"}


class FakeLLM:
    """Categorizes by crude keyword, with scripted confidence + one hallucination."""

    key = "fake"
    sends_data_off_device = False
    model = "fake-model"

    def __init__(self):
        self.calls: list[str] = []

    async def status(self):
        return {"provider": self.key, "endpoint": "http://127.0.0.1:1",
                "endpoint_is_local": True, "reachable": True, "model_present": True,
                "model": self.model, "models": [self.model]}

    async def complete_json(self, *, system, user, schema):
        self.calls.append(user)
        items = []
        for line in user.splitlines():
            if ". " not in line or not line[0].isdigit():
                continue
            index = int(line.split(".")[0])
            text = line.upper()
            if "STREAMMAX" in text or "MELODIFY" in text or "CLOUDBOX" in text:
                items.append({"index": index, "category": "Subscriptions",
                              "confidence": 0.95, "reason": "subscription"})
            elif "OLIVE & VINE" in text or "RAMEN" in text or "TAQUERIA" in text:
                items.append({"index": index, "category": "Dining",
                              "confidence": 0.9, "reason": "restaurant"})
            elif "SQ *" in text or "TST*" in text or "POS DEBIT" in text:
                items.append({"index": index, "category": "Dining",
                              "confidence": 0.45, "reason": "ambiguous descriptor"})
            elif "COSTCO" in text:
                items.append({"index": index, "category": "Wholesale Clubs",  # hallucinated
                              "confidence": 0.97, "reason": "made-up category"})
            else:
                items.append({"index": index, "category": "Shopping",
                              "confidence": 0.82, "reason": "default"})
        return LLMResponse(parsed={"items": items}, model=self.model,
                           input_tokens=100, output_tokens=50, latency_ms=12)


class DownLLM:
    key = "ollama"
    sends_data_off_device = False
    model = "qwen2.5:7b-instruct"

    async def status(self):
        return {"provider": self.key, "endpoint": "http://127.0.0.1:11434",
                "endpoint_is_local": True, "reachable": False, "model_present": False,
                "model": self.model, "models": []}

    async def complete_json(self, **kwargs):
        raise LLMUnavailable("Ollama isn't running on this machine. Install it and "
                             "run `ollama pull qwen2.5:7b-instruct`.")


@pytest.fixture
def fake_llm(monkeypatch):
    import app.providers.llm as llm_module

    fake = FakeLLM()
    monkeypatch.setattr(llm_module, "_provider", fake)
    return fake


@pytest.fixture
def down_llm(monkeypatch):
    import app.providers.llm as llm_module

    monkeypatch.setattr(llm_module, "_provider", DownLLM())


async def _synced_jordan(client):
    assert (await client.post("/api/auth/register", json=JORDAN)).status_code == 201
    assert (await client.post("/api/sync")).status_code == 200


async def test_two_pass_categorization(client, fake_llm):
    await _synced_jordan(client)
    resp = await client.post("/api/categorize/run", json={"limit": 5000})
    assert resp.status_code == 200
    s = resp.json()

    # Rules caught the deterministic bulk without any model involvement.
    assert s["rules_applied"] > 50
    assert s["sent_to_model"] == s["examined"] - s["rules_applied"]
    assert s["batches"] >= 1
    assert not s["model_unavailable"]

    # Transfers never reached the model.
    for prompt in fake_llm.calls:
        assert "ONLINE TRANSFER TO SAVINGS" not in prompt
        assert "PAYROLL" not in prompt

    # Ambiguous descriptors landed in review with a low-confidence suggestion.
    queue = (await client.get("/api/review")).json()
    assert queue["total"] > 0
    ambiguous = [i for i in queue["items"] if i["description"].startswith(("SQ *", "TST*"))]
    assert ambiguous, "ambiguous merchants must land in the review queue"
    assert all(i["confidence"] is None or i["confidence"] < 0.8 for i in queue["items"])
    suggested = [i for i in ambiguous if i["suggested_category"] == "Dining"]
    assert suggested, "low-confidence suggestions should be attached, not auto-applied"

    # Hallucinated categories never enter the ledger.
    costco = (await client.get("/api/transactions",
                               params={"q": "COSTCO", "limit": 20})).json()
    assert costco and all(r["category_id"] is None for r in costco)

    # High-confidence LLM rows applied and are NOT in review.
    stream = (await client.get("/api/transactions",
                               params={"q": "STREAMMAX", "limit": 5})).json()
    assert all(r["category_source"] == "llm" and r["category_confidence"] >= 0.8
               for r in stream)
    assert not any("STREAMMAX" in i["description"] for i in queue["items"])

    # ai_calls recorded the batches.
    status = (await client.get("/api/ai/status")).json()
    assert status["totals"]["calls"] == s["batches"]
    assert status["totals"]["input_tokens"] > 0


async def test_corrections_beat_the_model(client, fake_llm):
    await _synced_jordan(client)
    categories = {c["name"]: c["id"] for c in (await client.get("/api/categories")).json()}
    rows = (await client.get("/api/transactions",
                             params={"q": "SQ *BLUE STEM", "limit": 1})).json()
    await client.patch(f"/api/transactions/{rows[0]['id']}/category",
                       json={"category_id": categories["Dining"]})

    await client.post("/api/categorize/run", json={"limit": 5000})
    # Every SQ *BLUE STEM row was categorized by rules, and none reached the model.
    blue = (await client.get("/api/transactions",
                             params={"q": "SQ *BLUE STEM", "limit": 100})).json()
    assert all(r["category_id"] == categories["Dining"] for r in blue)
    assert all(r["category_source"] in ("rules", "user") for r in blue)
    for prompt in fake_llm.calls:
        assert "SQ *BLUE STEM" not in prompt


async def test_degrades_without_model(client, down_llm):
    await _synced_jordan(client)
    resp = await client.post("/api/categorize/run", json={"limit": 5000})
    assert resp.status_code == 200
    s = resp.json()
    assert s["rules_applied"] > 0            # rules still ran
    assert s["model_unavailable"] is True
    assert "ollama pull" in s["model_message"]

    status = (await client.get("/api/ai/status")).json()
    assert status["reachable"] is False
    assert "ollama pull" in status["enable_hint"]


async def test_loopback_guard_refuses_remote_endpoint(client, monkeypatch):
    from app.providers.llm.ollama import OllamaProvider

    provider = OllamaProvider("http://model.example.com:11434", "qwen2.5:7b-instruct")
    status = await provider.status()
    assert status["endpoint_is_local"] is False
    with pytest.raises(LLMUnavailable) as exc:
        await provider.complete_json(system="s", user="u", schema={})
    assert "refuses" in str(exc.value)


async def test_review_resolve_with_bulk_apply(client, fake_llm, tmp_path):
    await _synced_jordan(client)
    await client.post("/api/categorize/run", json={"limit": 5000})
    categories = {c["name"]: c["id"] for c in (await client.get("/api/categories")).json()}

    queue = (await client.get("/api/review", params={"limit": 200})).json()
    target = next(i for i in queue["items"] if i["description"] == "SQ *BLUE STEM")
    before_total = queue["total"]

    resp = await client.post(f"/api/review/{target['id']}/resolve",
                             json={"category_id": categories["Dining"],
                                   "apply_to_matching": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["resolved"] > 1, "bulk apply should clear every matching row"

    after = (await client.get("/api/review", params={"limit": 200})).json()
    assert after["total"] == before_total - body["resolved"]
    assert not any(i["description"] == "SQ *BLUE STEM" for i in after["items"])

    # Tier-3 capture: the correction landed in the training JSONL.
    me = (await client.get("/api/auth/me")).json()
    jsonl = tmp_path / "data" / str(me["id"]) / "training" / "corrections.jsonl"
    assert jsonl.exists()
    record = json.loads(jsonl.read_text().splitlines()[-1])
    assert record["output"]["category"] == "Dining"
    assert record["input"]["description"] == "SQ *BLUE STEM"


async def test_model_choice_persists(client, fake_llm):
    await _synced_jordan(client)
    resp = await client.put("/api/ai/model", json={"model": "qwen2.5:3b-instruct"})
    assert resp.status_code == 200
    from app.services.app_settings import read_app_settings

    assert read_app_settings()["ollama_model"] == "qwen2.5:3b-instruct"
    resp = await client.put("/api/ai/model", json={"model": "not-a-model"})
    assert resp.status_code == 422
