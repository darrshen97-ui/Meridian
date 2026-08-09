"""Document upload / preview / import endpoints. Thin over IngestionService."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.routers.deps import CurrentUser, DbSession
from app.services.ingestion import IngestionError, IngestionService

router = APIRouter(prefix="/api/documents", tags=["documents"])


def register_exception_handler(app) -> None:
    @app.exception_handler(IngestionError)
    async def handle_ingestion_error(request: Request, exc: IngestionError):
        return JSONResponse(status_code=exc.status_code,
                            content={"detail": exc.message, **exc.detail})


class ImportRequest(BaseModel):
    account_id: int | None = None
    create_account: bool = False


@router.post("/upload")
async def upload(files: list[UploadFile], session: DbSession, user: CurrentUser):
    """Multi-file upload; each file gets an independent result (brief §10)."""
    service = IngestionService(session)
    results = []
    for f in files:
        content = await f.read()
        try:
            doc = await service.upload(user.id, f.filename or "statement", content)
            results.append({"filename": f.filename, "status": "uploaded",
                            "document": asdict(doc)})
        except IngestionError as exc:
            await session.rollback()
            results.append({"filename": f.filename, "status": "rejected",
                            "error": exc.message, **exc.detail})
    return results


@router.get("/{document_id}/preview")
async def preview(document_id: int, session: DbSession, user: CurrentUser):
    p = await IngestionService(session).preview(user.id, document_id)
    return {
        "document": asdict(p.document),
        "parser": p.parser,
        "account_hint": p.account_hint,
        "matched_accounts": [asdict(a) for a in p.matched_accounts],
        "transactions": p.transactions,
        "period_start": p.period_start,
        "period_end": p.period_end,
        "opening_balance_minor": p.opening_balance_minor,
        "closing_balance_minor": p.closing_balance_minor,
        "problems": p.problems,
        "notes": p.notes,
    }


@router.post("/{document_id}/import")
async def import_document(document_id: int, body: ImportRequest,
                          session: DbSession, user: CurrentUser):
    result = await IngestionService(session).import_document(
        user.id, document_id, account_id=body.account_id,
        create_account=body.create_account)
    return asdict(result)


@router.get("/{document_id}/transactions")
async def document_transactions(document_id: int, session: DbSession, user: CurrentUser):
    from app.repositories.ledger import TransactionRepository

    rows = await TransactionRepository(session).list_by_document(user.id, document_id)
    return [asdict(r) for r in rows]
