"""Two-pass categorization (brief §12).

Pass 1 — deterministic rules: the user's own corrections first (they always
beat a fresh model guess), then generic built-in merchant patterns. Most
transactions never reach the model.

Pass 2 — local LLM in small batches with schema-constrained output and few-shot
personalization retrieved from the user's correction history (tier 2).
Confidence < 0.80 never auto-applies; it lands in the review queue as a
suggestion. Anything malformed or hallucinated goes to review, never the ledger.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction
from app.providers.llm import LLMError, LLMUnavailable
from app.repositories.audit import AuditRepository
from app.repositories.ledger import CategoryRepository, UserCorrectionRepository
from app.services.ai import AIService
from app.services.dedupe import normalize_description

BATCH_SIZE = 15
CONFIDENCE_FLOOR = 0.80
FEW_SHOT_LIMIT = 8

# Generic built-in patterns: substring of the normalized description → category.
# Deliberately brand-agnostic; user corrections always run first.
BUILTIN_RULES: list[tuple[str, str]] = [
    ("PAYROLL", "Income"), ("DIRECT DEP", "Income"), ("INTEREST", "Income"),
    ("RENT", "Housing"), ("MORTGAGE", "Housing"), ("PROPERTY MGMT", "Housing"),
    ("ELECTRIC", "Utilities"), ("GAS BILL", "Utilities"), ("INTERNET", "Utilities"),
    ("XFINITY", "Utilities"), ("WIRELESS", "Utilities"), ("T MOBILE", "Utilities"),
    ("INSURANCE", "Insurance"), ("INS", None),  # bare INS is too ambiguous: no rule
    ("GYM", "Health"), ("PHARMACY", "Health"),
    ("ATM WITHDRAWAL", "Cash"), ("CHECK #", "Cash"),
    ("UBER *TRIP", "Transport"), ("LYFT", "Transport"), ("TRIMET", "Transport"),
    ("SHELL OIL", "Transport"), ("CHEVRON", "Transport"), ("ARCO", "Transport"),
    ("AIR ", "Travel"), ("MARRIOTT", "Travel"), ("HOTEL", "Travel"),
    ("GROCERY", "Groceries"), ("MARKET", "Groceries"), ("SAFEWAY", "Groceries"),
    ("PAYMENT RECEIVED", "Transfers"), ("AUTOPAY", "Transfers"),
    ("LOAN PAYMENT", "Loan Payments"),
]

SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "category": {"type": "string"},
                    "confidence": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["index", "category", "confidence"],
            },
        }
    },
    "required": ["items"],
}

SYSTEM_PROMPT = (
    "You categorize personal-finance transactions. For every numbered transaction, "
    "pick exactly one category from the provided list — never invent a category. "
    "Use high confidence only for merchants you clearly recognize; use low "
    "confidence (0.4 or less) for cryptic or generic descriptors. Airlines and "
    "hotels are Travel; fuel and vehicle repair are Transport. Respond with JSON only."
)

# A small model is overconfident about processor descriptors that hide the real
# merchant. The cap is deterministic — these can only auto-apply via a user's own
# correction (rules pass), never via a model guess. Tested against the actual
# model during development (see docs/DECISIONS.md D-017).
CRYPTIC_DESCRIPTOR = re.compile(
    r"^(SQ \*|TST\*|PP\*|PAYPAL \*|POS DEBIT|IC\*|CKE\*|VESTA \*|GPC\*)")
CRYPTIC_CONFIDENCE_CAP = 0.5


class CategorizationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.categories = CategoryRepository(session)
        self.corrections = UserCorrectionRepository(session)
        self.audit = AuditRepository(session)
        self.ai = AIService(session)

    async def run(self, user_id: int, *, limit: int = 500) -> dict:
        rows = list(await self.session.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.category_id.is_(None),
                Transaction.pending.is_(False),
            ).order_by(Transaction.posted_date.desc()).limit(limit)))

        categories = await self.categories.list(user_id)
        by_name = {c.name: c.id for c in categories}
        summary = {"examined": len(rows), "rules_applied": 0, "llm_applied": 0,
                   "llm_suggested": 0, "sent_to_model": 0, "model_unavailable": False,
                   "model_message": None, "batches": 0, "few_shot_hit_rate": None}

        # -- Pass 1: deterministic rules --------------------------------------
        correction_map = await self._correction_map(user_id)
        remaining: list[Transaction] = []
        for t in rows:
            category_id = self._match_rules(t, correction_map, by_name)
            if category_id is not None:
                t.category_id = category_id
                t.category_source = "rules"
                t.category_confidence = 1.0
                summary["rules_applied"] += 1
            else:
                remaining.append(t)

        # -- Pass 2: local LLM in small batches -------------------------------
        hits = 0
        try:
            for start in range(0, len(remaining), BATCH_SIZE):
                batch = remaining[start:start + BATCH_SIZE]
                summary["batches"] += 1
                summary["sent_to_model"] += len(batch)
                hits += await self._llm_batch(user_id, batch, by_name, correction_map,
                                              summary)
        except LLMUnavailable as exc:
            summary["model_unavailable"] = True
            summary["model_message"] = exc.message
        except LLMError as exc:
            summary["model_unavailable"] = True
            summary["model_message"] = exc.message

        if summary["sent_to_model"]:
            summary["few_shot_hit_rate"] = round(hits / summary["sent_to_model"], 3)
        await self.audit.append(user_id, event="categorize.run", detail={
            k: summary[k] for k in ("examined", "rules_applied", "llm_applied",
                                    "llm_suggested", "sent_to_model",
                                    "few_shot_hit_rate")})
        await self.session.commit()
        return summary

    # -- Rules ---------------------------------------------------------------

    async def _correction_map(self, user_id: int) -> dict[str, int]:
        """Newest correction wins per pattern."""
        out: dict[str, int] = {}
        for c in reversed(await self.corrections.list(user_id)):
            out[c.merchant_pattern] = c.category_id
        return out

    def _match_rules(self, t: Transaction, corrections: dict[str, int],
                     by_name: dict[str, int]) -> int | None:
        normalized = normalize_description(t.merchant or t.description_raw)
        full = normalize_description(t.description_raw)
        # The user's own memory first — strongest form of learning in the system.
        if normalized in corrections:
            return corrections[normalized]
        if full in corrections:
            return corrections[full]
        if t.type == "transfer":
            return by_name.get("Transfers")
        for needle, category in BUILTIN_RULES:
            if category and needle in full:
                return by_name.get(category)
        return None

    # -- LLM -----------------------------------------------------------------

    def _few_shot(self, batch: list[Transaction], corrections: dict[str, int],
                  id_to_name: dict[int, str]) -> tuple[list[str], int]:
        """Tier 2: the user's relevant past corrections as worked examples."""
        batch_tokens = [
            set(normalize_description(t.merchant or t.description_raw).split())
            for t in batch
        ]
        examples: list[str] = []
        hit_rows: set[int] = set()
        for pattern, category_id in corrections.items():
            pattern_tokens = {tok for tok in pattern.split() if len(tok) >= 3}
            if not pattern_tokens:
                continue
            matched = [i for i, tokens in enumerate(batch_tokens)
                       if pattern_tokens & tokens]
            if matched and len(examples) < FEW_SHOT_LIMIT:
                name = id_to_name.get(category_id)
                if name:
                    examples.append(f'This user files "{pattern}" under {name}.')
                    hit_rows.update(matched)
        return examples, len(hit_rows)

    async def _llm_batch(self, user_id: int, batch: list[Transaction],
                         by_name: dict[str, int], corrections: dict[str, int],
                         summary: dict) -> int:
        id_to_name = {v: k for k, v in by_name.items()}
        examples, hit_count = self._few_shot(batch, corrections, id_to_name)

        lines = [f"{i}. {t.description_raw} ({'+' if t.amount_minor > 0 else '-'}"
                 f"${abs(t.amount_minor) / 100:.2f})"
                 for i, t in enumerate(batch)]
        user_prompt = "Categories: " + ", ".join(sorted(by_name)) + "\n\n"
        if examples:
            user_prompt += "This user's own filing habits:\n" + "\n".join(examples) + "\n\n"
        user_prompt += "Transactions:\n" + "\n".join(lines)

        result = await self.ai.call_json(user_id, feature="categorization",
                                         system=SYSTEM_PROMPT, user=user_prompt,
                                         schema=SCHEMA)
        items = result.parsed.get("items", [])
        for item in items:
            try:
                t = batch[int(item["index"])]
                category_name = str(item["category"])
                confidence = max(0.0, min(1.0, float(item["confidence"])))
            except (KeyError, ValueError, TypeError, IndexError):
                continue  # malformed → stays uncategorized → review queue
            category_id = by_name.get(category_name)
            if category_id is None:
                continue  # hallucinated category → review queue, never the ledger
            if CRYPTIC_DESCRIPTOR.match(t.description_raw.upper()):
                confidence = min(confidence, CRYPTIC_CONFIDENCE_CAP)
            t.category_id = category_id
            t.category_source = "llm"
            t.category_confidence = confidence
            if confidence >= CONFIDENCE_FLOOR:
                summary["llm_applied"] += 1
            else:
                summary["llm_suggested"] += 1  # a suggestion awaiting review
        return hit_count
