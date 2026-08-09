"""PDF statement rendering — reportlab, deterministic output.

Three deliberately different layouts so the parsers do genuine work (brief §9):
  * American Bank — MM/DD/YY dates, Date|Description|Amount|Balance columns
  * Chase — 'Mon DD, YYYY' dates, summary block, Date|Description|Amount
  * Discover — MM/DD/YYYY, Trans Date|Post Date|Description|Amount column order
Credit-card statements print purchases as positive numbers (industry convention),
so parsers must normalize signs per institution. Long tables split across pages
with repeated header rows (Chase Sapphire December spans a page break).
"""
from __future__ import annotations

import datetime as dt

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .core import AccountSpec, Ledger, Txn, fmt_money, month_days

INK = colors.HexColor("#16181D")
MUTED = colors.HexColor("#6E7178")
RULE = colors.HexColor("#C9C9C6")

BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK)
H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=INK)
SMALL = ParagraphStyle("small", fontName="Helvetica", fontSize=7.5, leading=9.5,
                       textColor=MUTED)
LABEL = ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=9, leading=12,
                       textColor=INK)


def _table(data: list[list], widths: list[float], numeric_cols: list[int],
           header: bool = True) -> Table:
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]
    if header:
        style += [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
        ]
    for col in numeric_cols:
        style.append(("ALIGN", (col, 0), (col, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def _summary(pairs: list[tuple[str, str]]) -> Table:
    data = [[k, v] for k, v in pairs]
    t = Table(data, colWidths=[2.6 * inch, 1.6 * inch], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, INK),
        ("LINEABOVE", (0, -1), (-1, -1), 0.4, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def render_statement(path: str, led: Ledger, spec: AccountSpec,
                     year: int, month: int) -> None:
    first, last = month_days(year, month)
    txns = led.statement_txns(spec.key, year, month)
    begin = led.balance_before(spec.key, first)
    end = begin + sum(t.amount_minor for t in txns)

    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                            title=f"{spec.institution} Statement", author=spec.institution)
    story: list = []
    if spec.institution == "American Bank":
        _american_bank(story, led, spec, first, last, txns, begin, end)
    elif spec.institution == "Discover":
        _discover(story, led, spec, first, last, txns, begin, end)
    elif spec.type == "loan":
        _chase_loan(story, led, spec, first, last, txns, begin, end)
    else:
        _chase(story, led, spec, first, last, txns, begin, end)
    doc.build(story)


def _american_bank(story, led, spec, first, last, txns, begin, end) -> None:
    story.append(Paragraph("AMERICAN BANK", H1))
    story.append(Paragraph("PO Box 1200 · Portland, OR 97204 · americanbank.example", SMALL))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"{led.display_name.upper()} — "
                           f"{spec.display_name} — account XXXXXX{spec.mask}", LABEL))
    story.append(Paragraph(
        f"Statement period {first:%m/%d/%y} – {last:%m/%d/%y}", BODY))
    story.append(Spacer(1, 8))
    deposits = sum(t.amount_minor for t in txns if t.amount_minor > 0)
    withdrawals = -sum(t.amount_minor for t in txns if t.amount_minor < 0)
    story.append(_summary([
        ("Beginning balance", f"${fmt_money(begin)}"),
        ("Deposits & credits", f"${fmt_money(deposits)}"),
        ("Withdrawals & debits", f"${fmt_money(withdrawals)}"),
        ("Ending balance", f"${fmt_money(end)}"),
    ]))
    story.append(Spacer(1, 12))
    rows = [["Date", "Description", "Amount", "Balance"]]
    running = begin
    for t in txns:
        running += t.amount_minor
        rows.append([f"{t.stmt_date:%m/%d/%y}", t.description[:58],
                     fmt_money(t.amount_minor), fmt_money(running)])
    story.append(_table(rows, [0.7 * inch, 3.9 * inch, 1.1 * inch, 1.1 * inch], [2, 3]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("American Bank · Member FDIC · Questions: 1-800-555-0119", SMALL))


def _chase(story, led, spec, first, last, txns, begin, end) -> None:
    is_card = spec.type == "credit_card"
    story.append(Paragraph("CHASE", H1))
    story.append(Paragraph("JPMorgan Chase Bank, N.A. · chase.example", SMALL))
    story.append(Spacer(1, 10))
    title = "SAPPHIRE ACCOUNT STATEMENT" if is_card else "CHECKING ACCOUNT STATEMENT"
    story.append(Paragraph(title, LABEL))
    story.append(Paragraph(
        f"{first:%B %d, %Y} through {last:%B %d, %Y} · "
        f"Account ending in {spec.mask} · {led.display_name}", BODY))
    story.append(Spacer(1, 8))
    if is_card:
        payments = sum(t.amount_minor for t in txns if t.amount_minor > 0)
        purchases = -sum(t.amount_minor for t in txns if t.amount_minor < 0)
        story.append(_summary([
            ("Previous balance", f"${fmt_money(-begin)}"),
            ("Payments and credits", f"-${fmt_money(payments)}"),
            ("Purchases", f"${fmt_money(purchases)}"),
            ("New balance", f"${fmt_money(-end)}"),
        ]))
    else:
        deposits = sum(t.amount_minor for t in txns if t.amount_minor > 0)
        withdrawals = -sum(t.amount_minor for t in txns if t.amount_minor < 0)
        story.append(_summary([
            ("Beginning balance", f"${fmt_money(begin)}"),
            ("Deposits and additions", f"${fmt_money(deposits)}"),
            ("Electronic withdrawals", f"${fmt_money(withdrawals)}"),
            ("Ending balance", f"${fmt_money(end)}"),
        ]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("TRANSACTION DETAIL", LABEL))
    story.append(Spacer(1, 4))
    rows = [["Date", "Description", "Amount"]]
    for t in txns:
        # Card convention: purchases positive, payments/credits negative.
        amount = -t.amount_minor if is_card else t.amount_minor
        rows.append([f"{t.stmt_date:%b %d, %Y}", t.description[:60], fmt_money(amount)])
    story.append(_table(rows, [1.1 * inch, 4.4 * inch, 1.3 * inch], [2]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Chase · Questions: 1-800-555-0182", SMALL))


def _discover(story, led, spec, first, last, txns, begin, end) -> None:
    story.append(Paragraph("DISCOVER", H1))
    story.append(Paragraph("Discover Bank · discover.example", SMALL))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Discover it® Card — account ending in {spec.mask}", LABEL))
    story.append(Paragraph(
        f"Open date {first:%m/%d/%Y} — close date {last:%m/%d/%Y} · {led.display_name}",
        BODY))
    story.append(Spacer(1, 8))
    payments = sum(t.amount_minor for t in txns if t.amount_minor > 0)
    purchases = -sum(t.amount_minor for t in txns if t.amount_minor < 0)
    story.append(_summary([
        ("Previous balance", f"${fmt_money(-begin)}"),
        ("Payments and credits", f"-${fmt_money(payments)}"),
        ("Purchases", f"${fmt_money(purchases)}"),
        ("New balance", f"${fmt_money(-end)}"),
    ]))
    story.append(Spacer(1, 12))
    rows = [["Trans. Date", "Post Date", "Description", "Amount"]]
    for t in txns:
        trans_date = t.date if t.in_provider else t.stmt_date
        rows.append([f"{trans_date:%m/%d/%Y}", f"{t.stmt_date:%m/%d/%Y}",
                     t.description[:52], fmt_money(-t.amount_minor)])
    story.append(_table(rows, [0.95 * inch, 0.95 * inch, 3.7 * inch, 1.2 * inch], [3]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Discover · Questions: 1-800-555-0301", SMALL))


def _chase_loan(story, led, spec, first, last, txns, begin, end) -> None:
    story.append(Paragraph("CHASE AUTO", H1))
    story.append(Paragraph("JPMorgan Chase Bank, N.A. · Auto Finance", SMALL))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Auto loan statement — account ending in {spec.mask}", LABEL))
    story.append(Paragraph(
        f"{first:%B %d, %Y} through {last:%B %d, %Y} · {led.display_name}", BODY))
    story.append(Spacer(1, 8))
    received = sum(t.amount_minor for t in txns if t.amount_minor > 0)
    story.append(_summary([
        ("Previous principal balance", f"${fmt_money(-begin)}"),
        ("Payments received", f"${fmt_money(received)}"),
        ("Remaining principal balance", f"${fmt_money(-end)}"),
    ]))
    story.append(Spacer(1, 12))
    rows = [["Date", "Activity", "Amount"]]
    for t in txns:
        rows.append([f"{t.stmt_date:%b %d, %Y}", t.description[:60],
                     fmt_money(t.amount_minor)])
    if -end == 0:
        rows.append([f"{last:%b %d, %Y}", "LOAN PAID IN FULL — ACCOUNT CLOSED", ""])
    story.append(_table(rows, [1.1 * inch, 4.4 * inch, 1.3 * inch], [2]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Chase Auto · Questions: 1-800-555-0244", SMALL))
