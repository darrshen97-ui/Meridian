"""OFX 1.02 (SGML) rendering for Chase checking — proves multi-format ingestion.

Deliberately overlaps the same account's PDF statements: PDF + OFX + provider feed
all describe the same rows, exercising cross-format dedupe (docs/DECISIONS.md D-002).
"""
from __future__ import annotations

from .core import Ledger, fmt_money, month_days, STATEMENT_MONTHS

HEADER = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

"""


def render_ofx_month(path: str, led: Ledger, account: str, year: int, month: int) -> None:
    first, last = month_days(year, month)
    txns = led.statement_txns(account, year, month)
    spec = led.account(account)
    ending = led.balance_before(account, first) + sum(t.amount_minor for t in txns)

    lines = [
        "<OFX>",
        "<SIGNONMSGSRSV1><SONRS><STATUS><CODE>0<SEVERITY>INFO</STATUS>",
        f"<DTSERVER>{last:%Y%m%d}120000<LANGUAGE>ENG",
        "<FI><ORG>Chase<FID>10898</FI></SONRS></SIGNONMSGSRSV1>",
        "<BANKMSGSRSV1><STMTTRNRS><TRNUID>1<STATUS><CODE>0<SEVERITY>INFO</STATUS>",
        "<STMTRS><CURDEF>USD",
        f"<BANKACCTFROM><BANKID>021000021<ACCTID>XXXXXX{spec.mask}"
        "<ACCTTYPE>CHECKING</BANKACCTFROM>",
        f"<BANKTRANLIST><DTSTART>{first:%Y%m%d}<DTEND>{last:%Y%m%d}",
    ]
    for t in txns:
        trntype = "CREDIT" if t.amount_minor > 0 else "DEBIT"
        amount = fmt_money(t.amount_minor).replace(",", "")
        lines += [
            "<STMTTRN>",
            f"<TRNTYPE>{trntype}",
            f"<DTPOSTED>{t.stmt_date:%Y%m%d}",
            f"<TRNAMT>{amount}",
            f"<FITID>{t.external_id}",
            f"<NAME>{t.description[:32]}",
            "</STMTTRN>",
        ]
    lines += [
        "</BANKTRANLIST>",
        f"<LEDGERBAL><BALAMT>{fmt_money(ending).replace(',', '')}"
        f"<DTASOF>{last:%Y%m%d}</LEDGERBAL>",
        "</STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>",
    ]
    with open(path, "w", newline="\r\n") as f:
        f.write(HEADER + "\n".join(lines) + "\n")


def render_all_ofx(out_dir, led: Ledger) -> list[str]:
    ofx_dir = out_dir / "jordan" / "ofx"
    ofx_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for (y, m) in STATEMENT_MONTHS:
        p = ofx_dir / f"chase_checking_7734_{y}-{m:02d}.ofx"
        render_ofx_month(str(p), led, "ch_chk_7734", y, m)
        written.append(str(p))
    return written
