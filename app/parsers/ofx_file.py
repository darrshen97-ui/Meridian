"""OFX/QFX parser — any institution, via ofxparse."""
from __future__ import annotations

import io
import warnings

from app.parsers.base import (
    AccountHint,
    ParsedStatement,
    ParsedTxn,
    ParseError,
)

ACCTTYPE_MAP = {"checking": "checking", "savings": "savings",
                "creditcard": "credit_card"}


class OfxStatementParser:
    name = "ofx"
    kind = "ofx"

    def matches(self, filename: str, head: bytes) -> bool:
        lowered = filename.lower()
        return lowered.endswith((".ofx", ".qfx")) or head.lstrip().startswith(
            (b"OFXHEADER", b"<OFX>", b"<?OFX"))

    def parse(self, filename: str, content: bytes) -> ParsedStatement:
        from ofxparse import OfxParser

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # ofxparse's own bs4 deprecations
                ofx = OfxParser.parse(io.BytesIO(content))
            account = ofx.account
            statement = account.statement
        except Exception as exc:
            raise ParseError(
                f"{filename} could not be read as OFX ({type(exc).__name__}). "
                "Export it again in OFX or QFX format.") from exc

        txns = [
            ParsedTxn(
                posted_date=t.date.date(),
                description=(t.payee or t.memo or "").strip(),
                amount_minor=int((t.amount * 100).to_integral_value()),
                external_id=t.id or None,
            )
            for t in statement.transactions
        ]
        number = (account.number or "").strip()
        org = getattr(account.institution, "organization", None) if account.institution \
            else None
        acct_type = ACCTTYPE_MAP.get(str(account.account_type).lower())
        closing = int((statement.balance * 100).to_integral_value()) \
            if statement.balance is not None else None
        return ParsedStatement(
            kind=self.kind,
            account=AccountHint(
                institution=org,
                mask=number[-4:] if len(number) >= 4 else None,
                account_type=acct_type,
            ),
            transactions=txns,
            period_start=statement.start_date.date() if statement.start_date else None,
            period_end=statement.end_date.date() if statement.end_date else None,
            closing_balance_minor=closing,
        )
