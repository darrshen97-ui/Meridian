"""Review queue: only low-confidence and unreviewed transactions (screen 5).

Resolving is the engine of the learning loop: every decision writes a tier-1
correction, appends a tier-3 training example, and can bulk-apply to all
matching unreviewed transactions in one keystroke.
"""
from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction
from app.models.base import utcnow
from app.repositories.audit import AuditRepository
from app.repositories.ledger import (
    CategoryRepository,
    TransactionRepository,
    UserCorrectionRepository,
)
from app.services.dedupe import normalize_description
from app.services.ledger import LedgerError
from app.services.training import append_training_example

QUEUE_FILTER = lambda user_id: (  # noqa: E731
    Transaction.user_id == user_id,
    Transaction.pending.is_(False),
    Transaction.reviewed_at.is_(None),
    (Transaction.category_id.is_(None)) | (Transaction.category_confidence < 0.8),
)


class ReviewService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.transactions = TransactionRepository(session)
        self.categories = CategoryRepository(session)
        self.corrections = UserCorrectionRepository(session)
        self.audit = AuditRepository(session)

    async def queue(self, user_id: int, *, limit: int = 100) -> dict:
        rows = list(await self.session.scalars(
            select(Transaction).where(*QUEUE_FILTER(user_id))
            .order_by(Transaction.posted_date.desc(), Transaction.id.desc())
            .limit(limit)))
        from sqlalchemy import func

        total = await self.session.scalar(
            select(func.count(Transaction.id)).where(*QUEUE_FILTER(user_id)))
        categories = {c.id: c.name for c in await self.categories.list(user_id)}
        return {
            "total": int(total or 0),
            "items": [{
                "id": t.id, "posted_date": t.posted_date.isoformat(),
                "description": t.description_raw, "merchant": t.merchant,
                "amount_minor": t.amount_minor, "account_id": t.account_id,
                "suggested_category_id": t.category_id,
                "suggested_category": categories.get(t.category_id),
                "confidence": t.category_confidence,
                "source": t.category_source,
            } for t in rows],
        }

    async def resolve(self, user_id: int, transaction_id: int, *,
                      category_id: int, apply_to_matching: bool) -> dict:
        category = await self.categories.get_visible(user_id, category_id)
        if category is None:
            raise LedgerError("That category doesn't exist.", status_code=404)
        target = await self.session.scalar(
            select(Transaction).where(Transaction.user_id == user_id,
                                      Transaction.id == transaction_id))
        if target is None:
            raise LedgerError("That transaction doesn't exist.", status_code=404)

        pattern = normalize_description(target.merchant or target.description_raw)
        resolved_ids = [target.id]
        self._apply(target, category_id)

        if apply_to_matching:
            candidates = list(await self.session.scalars(
                select(Transaction).where(*QUEUE_FILTER(user_id))))
            for t in candidates:
                if t.id == target.id:
                    continue
                if normalize_description(t.merchant or t.description_raw) == pattern:
                    self._apply(t, category_id)
                    resolved_ids.append(t.id)

        await self.corrections.add(user_id, merchant_pattern=pattern,
                                   category_id=category_id)
        append_training_example(
            user_id, description=target.description_raw, merchant=target.merchant,
            amount_minor=target.amount_minor, category_name=category.name)
        await self.audit.append(user_id, event="review.resolved", detail={
            "transaction_id": transaction_id, "category_id": category_id,
            "applied_to": len(resolved_ids), "pattern": pattern})
        await self.session.commit()
        return {"resolved": len(resolved_ids), "pattern": pattern,
                "category": category.name}

    @staticmethod
    def _apply(t: Transaction, category_id: int) -> None:
        t.category_id = category_id
        t.category_source = "user"
        t.category_confidence = 1.0
        t.reviewed_at = utcnow()
