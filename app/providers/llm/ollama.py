"""OllamaProvider — the active, fully local LLM provider."""
from __future__ import annotations

import json
import time

import httpx

from app.providers.llm.base import LLMResponse, LLMError, LLMUnavailable, \
    endpoint_is_loopback


class OllamaProvider:
    key = "ollama"
    sends_data_off_device = False

    def __init__(self, base_url: str, model: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _guard_local(self) -> None:
        if not endpoint_is_loopback(self.base_url):
            raise LLMUnavailable(
                f"The configured model endpoint ({self.base_url}) is not a loopback "
                "address. Meridian refuses to send financial data off this machine — "
                "point OLLAMA_BASE_URL at 127.0.0.1.")

    async def status(self) -> dict:
        local = endpoint_is_loopback(self.base_url)
        out = {"provider": self.key, "endpoint": self.base_url,
               "endpoint_is_local": local, "model": self.model,
               "reachable": False, "model_present": False, "models": []}
        if not local:
            return out
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
        except (httpx.HTTPError, ValueError, KeyError):
            return out
        out["reachable"] = True
        out["models"] = models
        out["model_present"] = any(
            m == self.model or m.split(":")[0] == self.model.split(":")[0]
            and m == self.model for m in models
        ) or self.model in models
        return out

    async def complete_json(self, *, system: str, user: str, schema: dict) -> LLMResponse:
        self._guard_local()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": schema,          # Ollama structured output
            "stream": False,
            "options": {"temperature": 0},
        }
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.ConnectError as exc:
            raise LLMUnavailable(
                "Ollama isn't running on this machine. Install it and run "
                f"`ollama pull {self.model}` to enable AI features.") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"The local model call failed ({type(exc).__name__}).") from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        if resp.status_code == 404:
            raise LLMUnavailable(
                f"The model {self.model} isn't pulled yet. Run "
                f"`ollama pull {self.model}` to enable AI features.")
        if resp.status_code != 200:
            raise LLMError(f"Ollama returned {resp.status_code}: {resp.text[:200]}")

        body = resp.json()
        content = body.get("message", {}).get("content", "")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError("The model returned malformed JSON.") from exc
        return LLMResponse(
            parsed=parsed, model=body.get("model", self.model),
            input_tokens=body.get("prompt_eval_count"),
            output_tokens=body.get("eval_count"),
            latency_ms=latency_ms,
        )
