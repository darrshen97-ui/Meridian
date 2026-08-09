"""Document repository — user-scoped, like everything else."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import DocumentInfo
from app.models import Document


def _map(r: Document) -> DocumentInfo:
    return DocumentInfo(
        id=r.id, account_id=r.account_id, kind=r.kind, filename=r.filename,
        period_start=r.period_start, period_end=r.period_end,
        parse_status=r.parse_status, parse_error=r.parse_error, uploaded_at=r.uploaded_at,
    )


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, *, kind: str, filename: str, stored_path: str,
                     sha256: str) -> DocumentInfo:
        row = Document(user_id=user_id, kind=kind, filename=filename,
                       stored_path=stored_path, sha256=sha256, parse_status="pending")
        self.session.add(row)
        await self.session.flush()
        return _map(row)

    async def get(self, user_id: int, document_id: int) -> DocumentInfo | None:
        row = await self._row(user_id, document_id)
        return _map(row) if row else None

    async def stored_path(self, user_id: int, document_id: int) -> str | None:
        row = await self._row(user_id, document_id)
        return row.stored_path if row else None

    async def find_by_sha(self, user_id: int, sha256: str) -> DocumentInfo | None:
        row = await self.session.scalar(
            select(Document).where(Document.user_id == user_id,
                                   Document.sha256 == sha256))
        return _map(row) if row else None

    async def update_parse_result(self, user_id: int, document_id: int, *,
                                  parse_status: str, parse_error: str | None = None,
                                  account_id: int | None = None,
                                  period_start: dt.date | None = None,
                                  period_end: dt.date | None = None) -> None:
        row = await self._row(user_id, document_id)
        if row is None:
            return
        row.parse_status = parse_status
        row.parse_error = parse_error
        if account_id is not None:
            row.account_id = account_id
        if period_start is not None:
            row.period_start = period_start
        if period_end is not None:
            row.period_end = period_end

    async def _row(self, user_id: int, document_id: int) -> Document | None:
        return await self.session.scalar(
            select(Document).where(Document.user_id == user_id,
                                   Document.id == document_id))
