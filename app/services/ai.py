"""AI call wrapper: every model call goes through here and is recorded in
ai_calls (latency and token counts matter for tuning even at zero cost)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AiCall
from app.providers.llm import LLMError, LLMResponse, LLMUnavailable, get_llm_provider


class AIService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.provider = get_llm_provider()

    async def call_json(self, user_id: int | None, *, feature: str, system: str,
                        user: str, schema: dict) -> LLMResponse:
        """One structured-output call, logged win or lose. Raises LLMUnavailable /
        LLMError for the caller to degrade on."""
        try:
            result = await self.provider.complete_json(
                system=system, user=user, schema=schema)
        except LLMUnavailable:
            raise
        except LLMError:
            self.session.add(AiCall(user_id=user_id, feature=feature,
                                    model=getattr(self.provider, "model", "unknown"),
                                    status="error"))
            raise
        self.session.add(AiCall(
            user_id=user_id, feature=feature, model=result.model,
            input_tokens=result.input_tokens, output_tokens=result.output_tokens,
            latency_ms=result.latency_ms, status="ok"))
        return result

    async def status(self, user_id: int) -> dict:
        provider_status = await self.provider.status()
        last = await self.session.scalar(
            select(AiCall).where(AiCall.user_id == user_id)
            .order_by(AiCall.id.desc()).limit(1))
        totals = (await self.session.execute(
            select(func.count(AiCall.id),
                   func.coalesce(func.sum(AiCall.input_tokens), 0),
                   func.coalesce(func.sum(AiCall.output_tokens), 0),
                   func.avg(AiCall.latency_ms))
            .where(AiCall.user_id == user_id, AiCall.status == "ok"))).one()
        return {
            **provider_status,
            "sends_data_off_device": self.provider.sends_data_off_device,
            "last_call": {
                "feature": last.feature, "status": last.status,
                "latency_ms": last.latency_ms,
                "at": last.created_at.isoformat() if last.created_at else None,
            } if last else None,
            "totals": {"calls": int(totals[0]), "input_tokens": int(totals[1]),
                       "output_tokens": int(totals[2]),
                       "avg_latency_ms": int(totals[3]) if totals[3] else None},
            "enable_hint": None if provider_status.get("model_present") else (
                "Install Ollama, then run: "
                f"ollama pull {provider_status.get('model', 'qwen2.5:7b-instruct')}"),
        }

    async def selftest(self, user_id: int) -> dict:
        """First-use latency check; recommends the 3B model when the 7B is slow."""
        schema = {"type": "object", "properties": {"category": {"type": "string"},
                                                   "confidence": {"type": "number"}},
                  "required": ["category", "confidence"]}
        result = await self.call_json(
            user_id, feature="selftest",
            system="You are a transaction categorizer. Respond with JSON only.",
            user='Categorize this transaction: "SAFEWAY #1442 GROCERY". '
                 'Choose from: Groceries, Dining, Transport.',
            schema=schema)
        await self.session.commit()
        slow = result.latency_ms > 20_000
        return {
            "latency_ms": result.latency_ms,
            "model": result.model,
            "acceptable": not slow,
            "recommendation": (
                "This machine runs the model comfortably." if not slow else
                "That took a while on this machine. Consider the smaller model: "
                "run `ollama pull qwen2.5:3b-instruct`, then choose it below."),
        }
