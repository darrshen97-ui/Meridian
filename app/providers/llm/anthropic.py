"""AnthropicProvider — OFF BY DEFAULT; sends data off-device if ever enabled.

Exists because the submitted course architecture references the Claude API and
the abstraction costs nothing (brief §12). Activating it requires BOTH
LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY, and Settings labels it plainly
as sending data off this machine. The product default is local, full stop.
"""
from __future__ import annotations

import json
import time

import httpx

from app.providers.llm.base import LLMResponse, LLMError, LLMUnavailable

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5"


class AnthropicProvider:
    key = "anthropic"
    sends_data_off_device = True

    def __init__(self, api_key: str | None, model: str = DEFAULT_MODEL,
                 timeout: float = 60.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def status(self) -> dict:
        return {
            "provider": self.key, "endpoint": API_URL, "endpoint_is_local": False,
            "model": self.model, "reachable": bool(self.api_key),
            "model_present": bool(self.api_key), "models": [],
            "warning": "This provider sends transaction data off this machine.",
        }

    async def complete_json(self, *, system: str, user: str, schema: dict) -> LLMResponse:
        if not self.api_key:
            raise LLMUnavailable(
                "The Anthropic provider is not configured (no API key) — and it is "
                "off by default because it sends data off-device. The local Ollama "
                "provider is the product default.")
        prompt = (f"{user}\n\nRespond with only a JSON object matching this schema, "
                  f"no prose:\n{json.dumps(schema)}")
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(API_URL, json={
                    "model": self.model,
                    "max_tokens": 2048,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}],
                }, headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                })
        except httpx.HTTPError as exc:
            raise LLMError(f"The Anthropic call failed ({type(exc).__name__}).") from exc
        latency_ms = int((time.monotonic() - started) * 1000)
        if resp.status_code != 200:
            raise LLMError(f"Anthropic returned {resp.status_code}: {resp.text[:200]}")
        body = resp.json()
        text = "".join(b.get("text", "") for b in body.get("content", []))
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError("The model returned malformed JSON.") from exc
        usage = body.get("usage", {})
        return LLMResponse(parsed=parsed, model=body.get("model", self.model),
                           input_tokens=usage.get("input_tokens"),
                           output_tokens=usage.get("output_tokens"),
                           latency_ms=latency_ms)
