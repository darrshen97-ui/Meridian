"""CSV export rendering — each platform's real-world column layout and quirks.

Venmo: multi-row header, leading empty column, "+ $x.xx"/"- $x.xx" amounts, monthly.
Cash App: flat header with fee and net columns, timezone-suffixed timestamps, monthly.
Binance: trade export, UTC timestamps, quantity+asset in one column, annual.
Gemini: separate fee column, split date/time columns, per-asset amount columns, annual.
"""
from __future__ import annotations

import csv
import datetime as dt

from .core import Ledger, Txn, month_days, STATEMENT_MONTHS


def _stmt_rows(led: Ledger, account: str, year: int, month: int) -> list[Txn]:
    return led.statement_txns(account, year, month)


def _money_venmo(minor: int) -> str:
    sign = "-" if minor < 0 else "+"
    a = abs(minor)
    return f"{sign} ${a // 100:,}.{a % 100:02d}"


def render_venmo_month(path: str, led: Ledger, year: int, month: int) -> None:
    first, last = month_days(year, month)
    rows = _stmt_rows(led, "venmo", year, month)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"Account Statement - (@jordan-reyes) - {first:%B %Y}"] + [""] * 10)
        w.writerow(["Account Activity"] + [""] * 10)
        w.writerow(["", "ID", "Datetime", "Type", "Status", "Note", "From", "To",
                    "Amount (total)", "Amount (fee)", "Funding Source"])
        for i, t in enumerate(rows, start=1):
            if "TRANSFER FROM" in t.description:
                kind, frm, to = "Standard Transfer", "", "Venmo balance"
                note = "Transfer from bank"
            elif t.amount_minor < 0:
                kind, frm, to = "Payment", "Jordan Reyes", t.description.replace(
                    "VENMO PAYMENT - ", "").title()
                note = "Payment"
            else:
                kind, frm, to = "Payment", t.description.replace(
                    "VENMO FROM ", "").title(), "Jordan Reyes"
                note = "Payment received"
            w.writerow(["", f"39{year}{month:02d}{i:04d}882",
                        f"{t.stmt_date:%Y-%m-%d}T{10 + (i % 9)}:{(i * 7) % 60:02d}:00",
                        kind, "Complete", note, frm, to,
                        _money_venmo(t.amount_minor), "", "Venmo balance"])


def render_cashapp_month(path: str, led: Ledger, year: int, month: int) -> None:
    rows = _stmt_rows(led, "cashapp", year, month)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Transaction ID", "Date", "Transaction Type", "Currency", "Amount",
                    "Fee", "Net Amount", "Notes", "Name of sender/receiver", "Account"])
        for i, t in enumerate(rows, start=1):
            if "ADD CASH" in t.description:
                kind, name = "Add Cash", "Jordan Reyes"
            elif t.amount_minor < 0:
                kind = "Cash App Pay"
                name = t.description.replace("CASH APP PAY - ", "").title()
            else:
                kind, name = "Received", t.description.replace(
                    "CASH APP RECEIVED - ", "").title()
            amount = t.amount_minor / 100
            w.writerow([f"ca-{year}{month:02d}-{i:05d}",
                        f"{t.stmt_date:%Y-%m-%d} {9 + (i % 10)}:{(i * 11) % 60:02d}:14 EDT",
                        kind, "USD", f"{amount:.2f}", "0", f"{amount:.2f}",
                        "", name, "Cash App"])


def render_binance_annual(path: str, led: Ledger) -> None:
    """Trade-history export: buys only, UTC timestamps, 0.1% fee in quote currency."""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date(UTC)", "Pair", "Side", "Price", "Executed", "Amount", "Fee"])
        for t in led.txns:
            if t.account != "binance" or not t.description.startswith("BUY ") \
                    or not t.in_statement:
                continue
            _, asset, qty, _, price = t.description.split(" ")
            usd = abs(t.amount_minor) / 100
            w.writerow([f"{t.stmt_date:%Y-%m-%d} 13:00:00", f"{asset}USDT", "BUY",
                        price.replace(",", ""), f"{qty} {asset}",
                        f"{usd:.2f} USDT", f"{usd * 0.001:.4f} USDT"])


def render_gemini_annual(path: str, led: Ledger) -> None:
    """Transaction-history export with a separate fee column (brief §9)."""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Time (UTC)", "Type", "Symbol", "USD Amount", "Fee (USD)",
                    "Asset Amount", "Price"])
        for t in led.txns:
            if t.account != "gemini" or not t.in_statement:
                continue
            usd = abs(t.amount_minor) / 100
            if t.description.startswith("BUY "):
                _, asset, qty, _, price = t.description.split(" ")
                w.writerow([f"{t.stmt_date:%Y-%m-%d}", "13:00:00", "Buy", f"{asset}USD",
                            f"{usd:.2f}", f"{usd * 0.0035:.2f}", f"{qty} {asset}",
                            price.replace(",", "")])
            elif t.description.startswith("SELL "):
                _, asset, qty, _, price = t.description.split(" ")
                w.writerow([f"{t.stmt_date:%Y-%m-%d}", "16:24:10", "Sell", f"{asset}USD",
                            f"{usd:.2f}", f"{usd * 0.0035:.2f}", f"-{qty} {asset}",
                            price.replace(",", "")])
            elif "DEPOSIT" in t.description:
                w.writerow([f"{t.stmt_date:%Y-%m-%d}", "09:00:00", "Deposit", "USD",
                            f"{usd:.2f}", "0.00", "", ""])
            elif "WITHDRAWAL" in t.description:
                w.writerow([f"{t.stmt_date:%Y-%m-%d}", "11:30:00", "Withdrawal", "USD",
                            f"-{usd:.2f}", "0.00", "", ""])


def render_all_csv(out_dir, led: Ledger) -> list[str]:
    written = []
    venmo_dir = out_dir / "jordan" / "exports" / "venmo"
    cashapp_dir = out_dir / "jordan" / "exports" / "cash_app"
    crypto_dir = out_dir / "jordan" / "exports"
    for d in (venmo_dir, cashapp_dir, crypto_dir):
        d.mkdir(parents=True, exist_ok=True)
    for (y, m) in STATEMENT_MONTHS:
        p = venmo_dir / f"venmo_statement_{y}-{m:02d}.csv"
        render_venmo_month(str(p), led, y, m)
        written.append(str(p))
        p = cashapp_dir / f"cash_app_report_{y}-{m:02d}.csv"
        render_cashapp_month(str(p), led, y, m)
        written.append(str(p))
    p = crypto_dir / "binance" / "binance_trades_2025-08-01_2026-07-31.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    render_binance_annual(str(p), led)
    written.append(str(p))
    p = crypto_dir / "gemini" / "gemini_transaction_history_2025-08-01_2026-07-31.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    render_gemini_annual(str(p), led)
    written.append(str(p))
    return written
