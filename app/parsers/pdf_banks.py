"""PDF statement parsers — one class per institution layout.

Each layout differs on purpose in the sample set (column order, date format,
sign convention); each parser normalizes to: negative = money out.
Lines that look like transaction rows but fail to parse are reported as
specific ParseProblems (page, line, reason) — never a generic failure.
"""
from __future__ import annotations

import datetime as dt
import io
import re

import pdfplumber

from app.parsers.base import (
    AccountHint,
    ParsedStatement,
    ParsedTxn,
    ParseError,
    ParseProblem,
    money_to_minor,
)

AMOUNT = r"-?[\d,]+\.\d{2}"


def _pdf_pages(content: bytes, filename: str) -> list[str]:
    try:
        with pdfplumber.open(io.BytesIO(content)) as doc:
            return [page.extract_text() or "" for page in doc.pages]
    except Exception as exc:  # corrupt/encrypted/non-PDF bytes
        raise ParseError(
            f"{filename} could not be opened as a PDF ({type(exc).__name__}). "
            "Re-download the statement and try again."
        ) from exc


def _find_money(text: str, label: str) -> int | None:
    m = re.search(rf"{re.escape(label)}\s+-?\$?({AMOUNT})", text)
    if not m:
        return None
    negative = "-$" in m.group(0) or m.group(0).split(label)[-1].strip().startswith("-")
    value = money_to_minor(m.group(1))
    return -value if negative and value > 0 else value


class AmericanBankPdfParser:
    """Date | Description | Amount | Balance rows, MM/DD/YY dates, signed amounts."""

    name = "american_bank_pdf"
    kind = "pdf_statement"
    ROW = re.compile(rf"^(\d{{2}}/\d{{2}}/\d{{2}})\s+(.+?)\s+({AMOUNT})\s+({AMOUNT})$")
    DATEISH = re.compile(r"^\d{2}/\d{2}/\d{2}\s")

    def matches(self, filename: str, head: bytes) -> bool:
        return filename.lower().endswith(".pdf") and b"AMERICAN BANK" in head

    def parse(self, filename: str, content: bytes) -> ParsedStatement:
        pages = _pdf_pages(content, filename)
        text = "\n".join(pages)

        mask_m = re.search(r"account X+(\d{4})", text)
        type_m = re.search(r"American Bank (Checking|Savings)", text)
        period_m = re.search(r"Statement period (\d{2}/\d{2}/\d{2}) . (\d{2}/\d{2}/\d{2})",
                             text)
        txns, problems = [], []
        for page_no, page in enumerate(pages, start=1):
            for line in page.splitlines():
                line = line.strip()
                m = self.ROW.match(line)
                if m:
                    txns.append(ParsedTxn(
                        posted_date=dt.datetime.strptime(m.group(1), "%m/%d/%y").date(),
                        description=m.group(2).strip(),
                        amount_minor=money_to_minor(m.group(3)),
                    ))
                elif self.DATEISH.match(line) and "period" not in line:
                    problems.append(ParseProblem(
                        page_no, line,
                        "Row starts with a date but doesn't match the "
                        "Date/Description/Amount/Balance layout."))
        return ParsedStatement(
            kind=self.kind,
            account=AccountHint(
                institution="American Bank",
                mask=mask_m.group(1) if mask_m else None,
                account_type=(type_m.group(1).lower() if type_m else None),
                display_name=f"American Bank {type_m.group(1)}" if type_m else None,
            ),
            transactions=txns,
            period_start=_d2(period_m.group(1)) if period_m else None,
            period_end=_d2(period_m.group(2)) if period_m else None,
            opening_balance_minor=_find_money(text, "Beginning balance"),
            closing_balance_minor=_find_money(text, "Ending balance"),
            problems=problems,
        )


class ChasePdfParser:
    """Checking, Sapphire card, and auto-loan layouts ('Mon DD, YYYY' dates).

    Card statements print purchases positive / payments negative → sign flipped.
    """

    name = "chase_pdf"
    kind = "pdf_statement"
    ROW = re.compile(rf"^([A-Z][a-z]{{2}} \d{{2}}, \d{{4}})\s+(.+?)\s+({AMOUNT})$")
    DATEISH = re.compile(r"^[A-Z][a-z]{2} \d{2}, \d{4}\s")

    OTHERS = (b"AMERICAN BANK", b"DISCOVER", b"ALLY BANK", b"CAPITAL ONE")

    def matches(self, filename: str, head: bytes) -> bool:
        return filename.lower().endswith(".pdf") and (
            b"CHASE" in head and not any(o in head for o in self.OTHERS)
        )

    def parse(self, filename: str, content: bytes) -> ParsedStatement:
        pages = _pdf_pages(content, filename)
        text = "\n".join(pages)

        is_card = "SAPPHIRE" in text
        is_loan = "Auto loan statement" in text
        mask_m = re.search(r"(?:ending in|account ending in) (\d{4})", text)
        period_m = re.search(
            r"(\w+ \d{1,2}, \d{4}) through (\w+ \d{1,2}, \d{4})", text)

        txns, problems = [], []
        for page_no, page in enumerate(pages, start=1):
            for line in page.splitlines():
                line = line.strip()
                if "PAID IN FULL" in line:
                    continue  # informational closure row on the final loan statement
                m = self.ROW.match(line)
                if m:
                    amount = money_to_minor(m.group(3))
                    txns.append(ParsedTxn(
                        posted_date=dt.datetime.strptime(m.group(1), "%b %d, %Y").date(),
                        description=m.group(2).strip(),
                        amount_minor=-amount if is_card else amount,
                    ))
                elif self.DATEISH.match(line) and "through" not in line:
                    problems.append(ParseProblem(
                        page_no, line,
                        "Row starts with a date but doesn't match the "
                        "Date/Description/Amount layout."))

        if is_card:
            opening = _find_money(text, "Previous balance")
            closing = _find_money(text, "New balance")
            opening = -opening if opening is not None else None
            closing = -closing if closing is not None else None
            account_type, display = "credit_card", "Chase Sapphire"
        elif is_loan:
            opening = _find_money(text, "Previous principal balance")
            closing = _find_money(text, "Remaining principal balance")
            opening = -opening if opening is not None else None
            closing = -closing if closing is not None else None
            account_type, display = "loan", "Chase Auto Loan"
        else:
            opening = _find_money(text, "Beginning balance")
            closing = _find_money(text, "Ending balance")
            account_type, display = "checking", "Chase Checking"

        return ParsedStatement(
            kind=self.kind,
            account=AccountHint(institution="Chase",
                                mask=mask_m.group(1) if mask_m else None,
                                account_type=account_type, display_name=display),
            transactions=txns,
            period_start=_dlong(period_m.group(1)) if period_m else None,
            period_end=_dlong(period_m.group(2)) if period_m else None,
            opening_balance_minor=opening,
            closing_balance_minor=closing,
            problems=problems,
        )


class DiscoverPdfParser:
    """Trans. Date | Post Date | Description | Amount, MM/DD/YYYY, purchases positive."""

    name = "discover_pdf"
    kind = "pdf_statement"
    ROW = re.compile(
        rf"^(\d{{2}}/\d{{2}}/\d{{4}})\s+(\d{{2}}/\d{{2}}/\d{{4}})\s+(.+?)\s+({AMOUNT})$")
    DATEISH = re.compile(r"^\d{2}/\d{2}/\d{4}\s")

    def matches(self, filename: str, head: bytes) -> bool:
        return filename.lower().endswith(".pdf") and b"DISCOVER" in head

    def parse(self, filename: str, content: bytes) -> ParsedStatement:
        pages = _pdf_pages(content, filename)
        text = "\n".join(pages)
        mask_m = re.search(r"ending in (\d{4})", text)
        period_m = re.search(
            r"Open date (\d{2}/\d{2}/\d{4}) . close date (\d{2}/\d{2}/\d{4})", text)

        txns, problems = [], []
        for page_no, page in enumerate(pages, start=1):
            for line in page.splitlines():
                line = line.strip()
                m = self.ROW.match(line)
                if m:
                    txns.append(ParsedTxn(
                        posted_date=_d4(m.group(2)),
                        transaction_date=_d4(m.group(1)),
                        description=m.group(3).strip(),
                        amount_minor=-money_to_minor(m.group(4)),
                    ))
                elif self.DATEISH.match(line) and "date" not in line.lower():
                    problems.append(ParseProblem(
                        page_no, line,
                        "Row starts with a date but doesn't match Discover's "
                        "TransDate/PostDate/Description/Amount layout."))

        opening = _find_money(text, "Previous balance")
        closing = _find_money(text, "New balance")
        return ParsedStatement(
            kind=self.kind,
            account=AccountHint(institution="Discover",
                                mask=mask_m.group(1) if mask_m else None,
                                account_type="credit_card",
                                display_name="Discover It Card"),
            transactions=txns,
            period_start=_d4(period_m.group(1)) if period_m else None,
            period_end=_d4(period_m.group(2)) if period_m else None,
            opening_balance_minor=-opening if opening is not None else None,
            closing_balance_minor=-closing if closing is not None else None,
            problems=problems,
        )


class AllyPdfParser:
    """ISO dates, unsigned Withdrawals/Deposits columns, running balance.

    Which way a row went is printed nowhere: both amount columns are unsigned and
    an empty cell leaves no trace in extracted text, so the two numbers after the
    description are (amount, balance) either way. The direction comes from the
    balance movement, and a printed amount that disagrees with that movement is
    reported rather than guessed at.
    """

    name = "ally_pdf"
    kind = "pdf_statement"
    ROW = re.compile(
        rf"^(\d{{4}}-\d{{2}}-\d{{2}})\s+(.+?)\s+({AMOUNT})\s+({AMOUNT})$")
    DATEISH = re.compile(r"^\d{4}-\d{2}-\d{2}\s")

    def matches(self, filename: str, head: bytes) -> bool:
        return filename.lower().endswith(".pdf") and b"ALLY BANK" in head

    def parse(self, filename: str, content: bytes) -> ParsedStatement:
        pages = _pdf_pages(content, filename)
        text = "\n".join(pages)

        mask_m = re.search(r"account ending (\d{4})", text)
        kind_m = re.search(r"Ally (Interest Checking|Online Savings)", text)
        period_m = re.search(
            r"Statement period (\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2})", text)
        opening = _find_money(text, "Beginning balance")

        running = opening
        txns, problems = [], []
        for page_no, page in enumerate(pages, start=1):
            for line in page.splitlines():
                line = line.strip()
                m = self.ROW.match(line)
                if not m:
                    if self.DATEISH.match(line):
                        problems.append(ParseProblem(
                            page_no, line,
                            "Row starts with a date but doesn't match Ally's "
                            "Date/Description/Withdrawals/Deposits/Balance layout."))
                    continue
                printed = money_to_minor(m.group(3))
                balance = money_to_minor(m.group(4))
                if running is None:
                    # No summary block to anchor on: fall back to the printed
                    # amount as a debit, the common case on these statements.
                    amount = -printed
                else:
                    amount = balance - running
                    if abs(amount) != printed:
                        problems.append(ParseProblem(
                            page_no, line,
                            f"Printed amount {m.group(3)} does not match the balance "
                            f"movement of {money_to_minor(m.group(4)) - running}; "
                            "the row was imported using the balance movement."))
                running = balance
                txns.append(ParsedTxn(
                    posted_date=dt.date.fromisoformat(m.group(1)),
                    description=m.group(2).strip(),
                    amount_minor=amount,
                ))

        kind = kind_m.group(1) if kind_m else None
        return ParsedStatement(
            kind=self.kind,
            account=AccountHint(
                institution="Ally Bank",
                mask=mask_m.group(1) if mask_m else None,
                account_type=("checking" if kind == "Interest Checking"
                              else "savings" if kind else None),
                display_name=f"Ally {kind}" if kind else None,
            ),
            transactions=txns,
            period_start=dt.date.fromisoformat(period_m.group(1)) if period_m else None,
            period_end=dt.date.fromisoformat(period_m.group(2)) if period_m else None,
            opening_balance_minor=opening,
            closing_balance_minor=_find_money(text, "Ending balance"),
            problems=problems,
        )


class CapitalOnePdfParser:
    """Trans Date | Post Date | Description | Amount, dates with no year.

    `Aug 03` carries no year at all; it has to be resolved against the billing
    period, whose year is printed once in the header. Purchases print positive
    (card convention) and credits print with a trailing minus.
    """

    name = "capital_one_pdf"
    kind = "pdf_statement"
    ROW = re.compile(
        rf"^([A-Z][a-z]{{2}} \d{{2}})\s+([A-Z][a-z]{{2}} \d{{2}})\s+(.+?)\s+({AMOUNT}-?)$")
    DATEISH = re.compile(r"^[A-Z][a-z]{2} \d{2}\s")
    PERIOD = re.compile(
        r"Billing period ([A-Z][a-z]{2} \d{2}) - ([A-Z][a-z]{2} \d{2}), (\d{4})")

    def matches(self, filename: str, head: bytes) -> bool:
        return filename.lower().endswith(".pdf") and b"CAPITAL ONE" in head

    def parse(self, filename: str, content: bytes) -> ParsedStatement:
        pages = _pdf_pages(content, filename)
        text = "\n".join(pages)

        mask_m = re.search(r"ending in (\d{4})", text)
        period = self.PERIOD.search(text)
        start = end_date = None
        if period:
            end_year = int(period.group(3))
            end_date = _dshort(period.group(2), end_year)
            start = _dshort(period.group(1), end_year)
            if start > end_date:  # period opened in the previous calendar year
                start = _dshort(period.group(1), end_year - 1)

        txns, problems = [], []
        for page_no, page in enumerate(pages, start=1):
            for line in page.splitlines():
                line = line.strip()
                m = self.ROW.match(line)
                if not m:
                    if self.DATEISH.match(line):
                        problems.append(ParseProblem(
                            page_no, line,
                            "Row starts with a date but doesn't match Capital One's "
                            "TransDate/PostDate/Description/Amount layout."))
                    continue
                raw = m.group(4)
                credit = raw.endswith("-")
                value = money_to_minor(raw.rstrip("-"))
                txns.append(ParsedTxn(
                    posted_date=_year_for(m.group(2), start, end_date),
                    transaction_date=_year_for(m.group(1), start, end_date),
                    description=m.group(3).strip(),
                    # Purchases print positive on a card statement: money out.
                    amount_minor=value if credit else -value,
                ))

        opening = _find_money(text, "Previous balance")
        closing = _find_money(text, "New balance")
        return ParsedStatement(
            kind=self.kind,
            account=AccountHint(institution="Capital One",
                                mask=mask_m.group(1) if mask_m else None,
                                account_type="credit_card",
                                display_name="Capital One Venture"),
            transactions=txns,
            period_start=start,
            period_end=end_date,
            opening_balance_minor=-opening if opening is not None else None,
            closing_balance_minor=-closing if closing is not None else None,
            problems=problems,
        )


def _dshort(s: str, year: int) -> dt.date:
    return dt.datetime.strptime(f"{s} {year}", "%b %d %Y").date()


def _year_for(short: str, start: dt.date | None, end: dt.date | None) -> dt.date | None:
    """Resolve 'Aug 03' against the billing period, which may span a year boundary."""
    if start is None or end is None:
        return None
    candidate = _dshort(short, end.year)
    if candidate < start:
        candidate = _dshort(short, end.year + 1)
    if candidate > end and start.year != end.year:
        candidate = _dshort(short, start.year)
    return candidate


def _d2(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%m/%d/%y").date()


def _d4(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%m/%d/%Y").date()


def _dlong(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%B %d, %Y").date()
