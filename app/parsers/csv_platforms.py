"""CSV export parsers — Venmo, Cash App, Binance, Gemini.

Each platform's export has its own quirks (multi-row headers, fee columns,
UTC timestamps); each parser normalizes to signed minor units, negative = out.
"""
from __future__ import annotations

import csv
import datetime as dt
import io

from app.parsers.base import (
    AccountHint,
    ParsedStatement,
    ParsedTxn,
    ParseError,
    ParseProblem,
    money_to_minor,
)


def _rows(content: bytes, filename: str) -> list[list[str]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ParseError(f"{filename} is not UTF-8 text; export it again as CSV.") from exc
    return list(csv.reader(io.StringIO(text)))


class VenmoCsvParser:
    """Venmo statement: two title rows, then a header with a leading empty column."""

    name = "venmo_csv"
    kind = "csv_export"

    def matches(self, filename: str, head: bytes) -> bool:
        return filename.lower().endswith(".csv") and head.startswith(b"Account Statement")

    def parse(self, filename: str, content: bytes) -> ParsedStatement:
        rows = _rows(content, filename)
        header_idx = next((i for i, r in enumerate(rows) if len(r) > 2 and r[1] == "ID"),
                          None)
        if header_idx is None:
            raise ParseError(
                f"{filename} doesn't contain Venmo's activity header row "
                "(blank column, then 'ID'). Export the monthly statement CSV.")
        header = rows[header_idx]
        col = {name: i for i, name in enumerate(header)}
        txns, problems = [], []
        for line_no, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
            if not any(row):
                continue
            try:
                when = dt.datetime.fromisoformat(row[col["Datetime"]]).date()
                amount = money_to_minor(row[col["Amount (total)"]])
                kind = row[col["Type"]]
                frm, to = row[col["From"]], row[col["To"]]
                if kind == "Standard Transfer":
                    desc = "TRANSFER FROM BANK"
                elif amount < 0:
                    desc = f"VENMO PAYMENT - {to.upper()}"
                else:
                    desc = f"VENMO FROM {frm.upper()}"
                txns.append(ParsedTxn(posted_date=when, description=desc,
                                      amount_minor=amount))
            except (KeyError, ValueError, IndexError) as exc:
                problems.append(ParseProblem(None, ",".join(row)[:120],
                                             f"Unreadable Venmo row ({exc})."))
        return ParsedStatement(
            kind=self.kind,
            account=AccountHint(institution="Venmo", account_type="payment_app",
                                display_name="Venmo Balance"),
            transactions=txns, problems=problems,
        )


class CashAppCsvParser:
    name = "cashapp_csv"
    kind = "csv_export"

    def matches(self, filename: str, head: bytes) -> bool:
        return filename.lower().endswith(".csv") and head.startswith(b"Transaction ID,Date,")

    def parse(self, filename: str, content: bytes) -> ParsedStatement:
        rows = _rows(content, filename)
        col = {name: i for i, name in enumerate(rows[0])}
        txns, problems = [], []
        for row in rows[1:]:
            if not any(row):
                continue
            try:
                when = dt.datetime.strptime(row[col["Date"]][:10], "%Y-%m-%d").date()
                amount = money_to_minor(row[col["Amount"]])
                kind = row[col["Transaction Type"]]
                name = row[col["Name of sender/receiver"]]
                if kind == "Add Cash":
                    desc = "ADD CASH"
                elif kind == "Received":
                    desc = f"CASH APP RECEIVED - {name.upper()}"
                else:
                    desc = f"CASH APP PAY - {name.upper()}"
                txns.append(ParsedTxn(posted_date=when, description=desc,
                                      amount_minor=amount,
                                      external_id=row[col["Transaction ID"]] or None))
            except (KeyError, ValueError, IndexError) as exc:
                problems.append(ParseProblem(None, ",".join(row)[:120],
                                             f"Unreadable Cash App row ({exc})."))
        return ParsedStatement(
            kind=self.kind,
            account=AccountHint(institution="Cash App", account_type="payment_app",
                                display_name="Cash App Balance"),
            transactions=txns, problems=problems,
        )


class BinanceCsvParser:
    """Trade-history export: UTC timestamps, quantity+asset combined, USDT fees."""

    name = "binance_csv"
    kind = "csv_export"

    def matches(self, filename: str, head: bytes) -> bool:
        return filename.lower().endswith(".csv") and head.startswith(b"Date(UTC),Pair,")

    def parse(self, filename: str, content: bytes) -> ParsedStatement:
        rows = _rows(content, filename)
        col = {name: i for i, name in enumerate(rows[0])}
        txns, problems = [], []
        for row in rows[1:]:
            if not any(row):
                continue
            try:
                when = dt.datetime.strptime(row[col["Date(UTC)"]],
                                            "%Y-%m-%d %H:%M:%S").date()
                usd = money_to_minor(row[col["Amount"]].replace(" USDT", ""))
                qty, asset = row[col["Executed"]].split(" ")
                price = int(float(row[col["Price"]]))
                side = row[col["Side"]]
                sign = -1 if side == "BUY" else 1
                txns.append(ParsedTxn(
                    posted_date=when,
                    description=f"{side} {asset} {qty} @ {price:,}",
                    amount_minor=sign * usd,
                ))
            except (KeyError, ValueError, IndexError) as exc:
                problems.append(ParseProblem(None, ",".join(row)[:120],
                                             f"Unreadable Binance row ({exc})."))
        return ParsedStatement(
            kind=self.kind,
            account=AccountHint(institution="Binance", account_type="crypto",
                                display_name="Binance (BTC, ETH)"),
            transactions=txns, problems=problems,
        )


class GeminiCsvParser:
    """Transaction-history export with a separate fee column.

    USD deposit/withdrawal rows are skipped (with a note) — cash movements come
    from the live provider feed; this export drives trade ingestion.
    """

    name = "gemini_csv"
    kind = "csv_export"

    def matches(self, filename: str, head: bytes) -> bool:
        return filename.lower().endswith(".csv") and head.startswith(b"Date,Time (UTC),Type,")

    def parse(self, filename: str, content: bytes) -> ParsedStatement:
        rows = _rows(content, filename)
        col = {name: i for i, name in enumerate(rows[0])}
        txns, problems, skipped = [], [], 0
        for row in rows[1:]:
            if not any(row):
                continue
            try:
                when = dt.datetime.strptime(row[col["Date"]], "%Y-%m-%d").date()
                kind = row[col["Type"]]
                usd = money_to_minor(row[col["USD Amount"]])
                if kind in ("Deposit", "Withdrawal"):
                    skipped += 1
                    continue
                qty_asset = row[col["Asset Amount"]].lstrip("-")
                qty, asset = qty_asset.split(" ")
                price = int(float(row[col["Price"]]))
                sign = -1 if kind == "Buy" else 1
                txns.append(ParsedTxn(
                    posted_date=when,
                    description=f"{kind.upper()} {asset} {qty} @ {price:,}",
                    amount_minor=sign * abs(usd),
                ))
            except (KeyError, ValueError, IndexError) as exc:
                problems.append(ParseProblem(None, ",".join(row)[:120],
                                             f"Unreadable Gemini row ({exc})."))
        notes = []
        if skipped:
            notes.append(f"Skipped {skipped} USD transfer rows — cash movements "
                         "come from the account sync, not the trade export.")
        return ParsedStatement(
            kind=self.kind,
            account=AccountHint(institution="Gemini", account_type="crypto",
                                display_name="Gemini (BTC, SOL)"),
            transactions=txns, problems=problems, notes=notes,
        )
