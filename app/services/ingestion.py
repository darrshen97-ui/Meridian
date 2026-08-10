"""Statement ingestion: upload → preview → confirm → import (brief §10).

Nothing is written to the ledger until the user confirms from the preview.
Uploaded files are retained under data/{user_id}/documents/ — filesystem-level
isolation matches the database's user scoping.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.models import AccountInfo, DocumentInfo
from app.parsers import ParsedStatement, ParseError, find_parser
from app.repositories.audit import AuditRepository
from app.repositories.documents import DocumentRepository
from app.repositories.ledger import AccountRepository, InstitutionRepository, \
    TransactionRepository
from app.services.dedupe import Existing, Incoming, dedupe_hash, match_incoming

INSTITUTION_KIND_BY_TYPE = {
    "checking": "bank", "savings": "bank", "credit_card": "credit", "loan": "loan",
    "payment_app": "payment_app", "crypto": "exchange", "investment": "brokerage",
}
LIQUID_TYPES = {"checking", "savings", "payment_app"}


class IngestionError(Exception):
    def __init__(self, message: str, status_code: int = 400, detail: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}


@dataclass
class Preview:
    document: DocumentInfo
    parser: str
    account_hint: dict
    matched_accounts: list[AccountInfo]
    transactions: list[dict]
    period_start: str | None
    period_end: str | None
    opening_balance_minor: int | None
    closing_balance_minor: int | None
    problems: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class ImportResult:
    document_id: int
    account_id: int
    imported: int
    merged: int
    problems: list[dict]


class IngestionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.documents = DocumentRepository(session)
        self.accounts = AccountRepository(session)
        self.institutions = InstitutionRepository(session)
        self.transactions = TransactionRepository(session)
        self.audit = AuditRepository(session)

    # -- Upload ------------------------------------------------------------

    MAX_UPLOAD_BYTES = 15 * 1024 * 1024

    async def upload(self, user_id: int, filename: str, content: bytes) -> DocumentInfo:
        if not content:
            raise IngestionError(f"{filename} is empty.")
        if len(content) > self.MAX_UPLOAD_BYTES:
            raise IngestionError(
                f"{filename} is {len(content) // (1024 * 1024)} MB — statements are "
                "expected under 15 MB. If this is a real statement, split the export.",
                status_code=413)
        sha = hashlib.sha256(content).hexdigest()
        already = await self.documents.find_by_sha(user_id, sha)
        if already is not None:
            raise IngestionError(
                f"{filename} was already uploaded on "
                f"{already.uploaded_at:%b %d, %Y} as \"{already.filename}\".",
                status_code=409, detail={"document_id": already.id})

        parser = find_parser(filename, content)
        if parser is None:
            raise IngestionError(
                f"{filename} doesn't match any supported statement format "
                "(PDF statement, Venmo/Cash App/Binance/Gemini CSV, or OFX/QFX).",
                status_code=422)

        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
        folder = get_settings().data_dir / str(user_id) / "documents"
        folder.mkdir(parents=True, exist_ok=True)
        stored = folder / f"{sha[:12]}_{safe_name}"
        stored.write_bytes(content)

        doc = await self.documents.create(user_id, kind=parser.kind, filename=filename,
                                          stored_path=str(stored), sha256=sha)
        await self.audit.append(user_id, event="document.uploaded",
                                detail={"document_id": doc.id, "filename": filename})
        await self.session.commit()
        return doc

    # -- Preview -----------------------------------------------------------

    async def preview(self, user_id: int, document_id: int) -> Preview:
        doc, content = await self._load(user_id, document_id)
        parser, parsed = await self._parse(user_id, doc, content)
        matched = await self._matching_accounts(user_id, parsed)
        return Preview(
            document=doc,
            parser=parser.name,
            account_hint=vars(parsed.account),
            matched_accounts=matched,
            transactions=[{
                "posted_date": t.posted_date.isoformat(),
                "transaction_date": t.transaction_date.isoformat()
                if t.transaction_date else None,
                "description": t.description,
                "amount_minor": t.amount_minor,
            } for t in parsed.transactions],
            period_start=parsed.period_start.isoformat() if parsed.period_start else None,
            period_end=parsed.period_end.isoformat() if parsed.period_end else None,
            opening_balance_minor=parsed.opening_balance_minor,
            closing_balance_minor=parsed.closing_balance_minor,
            problems=[vars(p) for p in parsed.problems],
            notes=parsed.notes,
        )

    # -- Import ------------------------------------------------------------

    async def import_document(self, user_id: int, document_id: int, *,
                              account_id: int | None = None,
                              create_account: bool = False) -> ImportResult:
        doc, content = await self._load(user_id, document_id)
        parser, parsed = await self._parse(user_id, doc, content)
        if not parsed.transactions:
            raise IngestionError(
                f"{doc.filename} parsed but contained no transactions to import.",
                status_code=422)

        account = await self._resolve_account(user_id, parsed, account_id, create_account)

        dates = [t.posted_date for t in parsed.transactions]
        window_from = min(dates + ([parsed.period_start] if parsed.period_start else []))
        window_to = max(dates + ([parsed.period_end] if parsed.period_end else []))
        existing_rows = await self.transactions.list_for_matching(
            user_id, account_id=account.id,
            date_from=window_from - dt.timedelta(days=4),
            date_to=window_to + dt.timedelta(days=4))

        incoming = [Incoming(index=i, posted_date=t.posted_date,
                             amount_minor=t.amount_minor, description=t.description)
                    for i, t in enumerate(parsed.transactions)]
        existing = [Existing(id=r.id, posted_date=r.posted_date,
                             amount_minor=r.amount_minor,
                             description=r.description_raw, dedupe_hash=r.dedupe_hash)
                    for r in existing_rows]
        result = match_incoming(account.id, incoming, existing)

        for index in result.to_insert:
            t = parsed.transactions[index]
            await self.transactions.create(
                user_id, account_id=account.id, posted_date=t.posted_date,
                description_raw=t.description, amount_minor=t.amount_minor,
                type="credit" if t.amount_minor > 0 else "debit",
                source="statement",
                dedupe_hash=dedupe_hash(account.id, t.posted_date, t.amount_minor,
                                        t.description),
                transaction_date=t.transaction_date,
                external_id=t.external_id,
                source_document_id=doc.id,
            )
        for index, existing_id in result.merged.items():
            await self.transactions.attach_document(
                user_id, existing_id, doc.id,
                statement_date=parsed.transactions[index].posted_date)

        await self.documents.update_parse_result(
            user_id, document_id,
            parse_status=parsed.status,
            parse_error="; ".join(p.reason for p in parsed.problems[:3]) or None,
            account_id=account.id,
            period_start=parsed.period_start, period_end=parsed.period_end)
        await self.audit.append(user_id, event="document.imported", detail={
            "document_id": doc.id, "account_id": account.id,
            "imported": len(result.to_insert), "merged": len(result.merged)})
        await self.session.commit()
        return ImportResult(document_id=doc.id, account_id=account.id,
                            imported=len(result.to_insert), merged=len(result.merged),
                            problems=[vars(p) for p in parsed.problems])

    # -- Internals ---------------------------------------------------------

    async def _load(self, user_id: int, document_id: int) -> tuple[DocumentInfo, bytes]:
        doc = await self.documents.get(user_id, document_id)
        if doc is None:
            raise IngestionError("Document not found.", status_code=404)
        path = await self.documents.stored_path(user_id, document_id)
        stored = Path(path) if path else None
        if stored is None or not stored.exists():
            raise IngestionError(
                f"The stored file for {doc.filename} is missing. Upload it again.",
                status_code=410)
        return doc, stored.read_bytes()

    async def _parse(self, user_id: int, doc: DocumentInfo, content: bytes):
        parser = find_parser(doc.filename, content)
        if parser is None:
            raise IngestionError(f"{doc.filename} no longer matches any parser.",
                                 status_code=422)
        try:
            parsed = parser.parse(doc.filename, content)
        except ParseError as exc:
            await self.documents.update_parse_result(
                user_id, doc.id, parse_status="failed", parse_error=exc.message)
            await self.session.commit()
            raise IngestionError(exc.message, status_code=422) from exc
        return parser, parsed

    async def _matching_accounts(self, user_id: int,
                                 parsed: ParsedStatement) -> list[AccountInfo]:
        accounts = await self.accounts.list(user_id)
        hint = parsed.account
        if hint.mask:
            matched = [a for a in accounts if a.mask == hint.mask]
        elif hint.institution:
            matched = [a for a in accounts
                       if hint.institution.lower() in a.display_name.lower()]
        else:
            matched = []
        return matched

    async def _resolve_account(self, user_id: int, parsed: ParsedStatement,
                               account_id: int | None,
                               create_account: bool) -> AccountInfo:
        if account_id is not None:
            account = await self.accounts.get(user_id, account_id)
            if account is None:
                raise IngestionError("That account doesn't exist.", status_code=404)
            return account

        matched = await self._matching_accounts(user_id, parsed)
        if len(matched) == 1:
            return matched[0]
        if len(matched) > 1:
            raise IngestionError(
                "More than one account matches this statement. Choose one.",
                status_code=409,
                detail={"candidates": [{"id": a.id, "display_name": a.display_name,
                                        "mask": a.mask} for a in matched]})

        if not create_account:
            hint = parsed.account
            raise IngestionError(
                "No existing account matches this statement "
                f"({hint.institution or 'unknown institution'}"
                f"{' ending in ' + hint.mask if hint.mask else ''}). "
                "Choose an account or create one.",
                status_code=409, detail={"candidates": [], "can_create": True})

        return await self._create_from_hint(user_id, parsed)

    async def _create_from_hint(self, user_id: int, parsed: ParsedStatement) -> AccountInfo:
        hint = parsed.account
        if not hint.institution or not hint.account_type:
            raise IngestionError(
                "This document doesn't identify its institution and account type, "
                "so an account can't be created automatically. Pick one instead.",
                status_code=422)
        institutions = await self.institutions.list(user_id)
        inst = next((i for i in institutions if i.name == hint.institution), None)
        inst_id = inst.id if inst else await self.institutions.create(
            user_id, name=hint.institution,
            kind=INSTITUTION_KIND_BY_TYPE.get(hint.account_type, "bank"))
        display = hint.display_name or hint.institution
        account_id = await self.accounts.create(
            user_id, institution_id=inst_id, display_name=display,
            type=hint.account_type, mask=hint.mask,
            is_liquid=hint.account_type in LIQUID_TYPES)
        account = await self.accounts.get(user_id, account_id)
        await self.audit.append(user_id, event="account.created_from_statement",
                                detail={"account_id": account_id,
                                        "institution": hint.institution})
        return account
