"""Parser registry and format detection."""
from __future__ import annotations

import io

from app.parsers.base import (  # noqa: F401
    AccountHint,
    ParsedStatement,
    ParsedTxn,
    ParseError,
    ParseProblem,
    PARSERS,
    StatementParser,
)
from app.parsers.csv_platforms import (
    BinanceCsvParser,
    CashAppCsvParser,
    GeminiCsvParser,
    VenmoCsvParser,
)
from app.parsers.ofx_file import OfxStatementParser
from app.parsers.pdf_banks import (
    AllyPdfParser,
    AmericanBankPdfParser,
    CapitalOnePdfParser,
    ChasePdfParser,
    DiscoverPdfParser,
)

# The registry: adding a new institution's layout = one class + one line here.
PARSERS[:] = [
    AmericanBankPdfParser(),
    ChasePdfParser(),
    DiscoverPdfParser(),
    AllyPdfParser(),
    CapitalOnePdfParser(),
    VenmoCsvParser(),
    CashAppCsvParser(),
    BinanceCsvParser(),
    GeminiCsvParser(),
    OfxStatementParser(),
]


def sniff_head(filename: str, content: bytes) -> bytes:
    """Detection material: first-page text for PDFs, leading bytes otherwise."""
    if filename.lower().endswith(".pdf") or content.startswith(b"%PDF"):
        try:
            import pdfplumber

            with pdfplumber.open(io.BytesIO(content)) as doc:
                return (doc.pages[0].extract_text() or "").encode()
        except Exception:
            return b""
    return content[:2048]


def find_parser(filename: str, content: bytes) -> StatementParser | None:
    head = sniff_head(filename, content)
    for parser in PARSERS:
        if parser.matches(filename, head):
            return parser
    return None
