from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


class AuditRepository:
    """Append-only audit log. Reads are user-scoped like everything else."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def append(self, user_id: int | None, *, event: str, detail: dict | None = None) -> None:
        self.session.add(
            AuditLog(user_id=user_id, event=event,
                     detail_json=json.dumps(detail) if detail else None)
        )

    async def list(self, user_id: int, *, limit: int = 200) -> list[dict]:
        rows = await self.session.scalars(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
        )
        return [
            {
                "id": r.id,
                "event": r.event,
                "detail": json.loads(r.detail_json) if r.detail_json else None,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
