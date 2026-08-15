"""Milestone 4 checkpoint: the generated dataset is deterministic, complete,
contains all 13 planted events from brief §9, and its documents are parseable.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from mockgen import jordan  # noqa: E402
from mockgen.core import STATEMENT_MONTHS, TODAY  # noqa: E402
from mockgen.output import build_ledgers  # noqa: E402

SAMPLE = PROJECT_ROOT / "sample_data"


@pytest.fixture(scope="module")
def ledgers():
    return build_ledgers()


def _events(led, tag):
    return [t for t in led.txns if t.event == tag]


class TestLedgerShape:
    def test_transaction_volumes(self, ledgers):
        led_j, led_p = ledgers
        assert 2100 <= len(led_j.txns) <= 2700   # brief: ~2,400
        assert 950 <= len(led_p.txns) <= 1300    # brief: ~1,100

    def test_determinism(self, ledgers):
        led_j, led_p = ledgers
        led_j2, led_p2 = build_ledgers()
        assert [vars(t) for t in led_j.txns] == [vars(t) for t in led_j2.txns]
        assert [vars(t) for t in led_p.txns] == [vars(t) for t in led_p2.txns]

    def test_profiles_share_no_merchants(self, ledgers):
        led_j, led_p = ledgers

        def brands(led):
            out = set()
            for t in led.txns:
                first = re.sub(r"[^A-Z]", "", t.description.split(" ")[0].upper())
                if len(first) >= 4:
                    out.add(first)
            return out

        overlap = brands(led_j) & brands(led_p)
        # Generic banking words that aren't merchants.
        allowed = {"TRANSFER", "ONLINE", "PAYMENT", "INTEREST", "WITHDRAWAL",
                   "DEPOSIT", "PAYPAL", "CASH", "BALANCE", "ACCOUNT"}
        assert overlap - allowed == set(), overlap - allowed

    def test_tail_is_provider_only(self, ledgers):
        led_j, _ = ledgers
        tail = [t for t in led_j.txns if t.date > dt.date(2026, 7, 31)]
        assert len(tail) > 10
        assert all(not t.in_statement for t in tail)
        assert all(t.date <= TODAY for t in led_j.txns)


class TestPlantedEvents:
    def test_01_duplicate_charge(self, ledgers):
        rows = _events(ledgers[0], "duplicate_charge")
        assert len(rows) == 2
        assert rows[0].description == rows[1].description
        assert rows[0].amount_minor == rows[1].amount_minor
        assert abs((rows[0].date - rows[1].date).days) == 2
        assert {r.account for r in rows} == {"ch_cc_1902"}
        assert rows[0].date.strftime("%Y-%m") == "2026-02"

    def test_02_missing_in_provider(self, ledgers):
        (row,) = _events(ledgers[0], "missing_in_provider")
        assert row.in_statement and not row.in_provider
        assert (row.account, row.date.strftime("%Y-%m")) == ("ab_chk_4417", "2025-11")

    def test_03_never_cleared_pending(self, ledgers):
        (row,) = _events(ledgers[0], "never_cleared_pending")
        assert row.pending and row.in_provider and not row.in_statement
        assert (row.account, row.date.strftime("%Y-%m")) == ("disc_6088", "2026-03")

    def test_04_subscription_increase(self, ledgers):
        led = ledgers[0]
        prices = {(t.date.year, t.date.month): -t.amount_minor
                  for t in led.txns if t.merchant == "StreamMax"}
        assert prices[(2025, 12)] == 1599
        assert prices[(2026, 1)] == 2299
        assert prices[(2026, 7)] == 2299

    def test_05_card_compromise(self, ledgers):
        led = ledgers[0]
        fraud = [t for t in _events(led, "card_compromise") if t.type == "debit"]
        assert len(fraud) == 3
        assert {t.account for t in fraud} == {"ab_chk_8123"}
        span = max(t.date for t in fraud) - min(t.date for t in fraud)
        assert span.days <= 2
        spec = led.account("ab_chk_8123")
        assert spec.closed_at == dt.date(2026, 6, 20)
        # Spending that used ••8123 resumes on ••4417 after closure.
        july_groceries = [t for t in led.txns
                         if t.category == "Groceries" and t.account == "ab_chk_4417"
                         and t.date >= dt.date(2026, 7, 1)]
        assert july_groceries
        assert not [t for t in led.txns
                    if t.account == "ab_chk_8123" and t.date > spec.closed_at]

    def test_06_ambiguous_merchants(self, ledgers):
        led = ledgers[0]
        n = sum(1 for t in led.txns if t.description in jordan.AMBIGUOUS)
        assert n >= 40

    def test_07_seasonal_spike(self, ledgers):
        led = ledgers[0]

        def discretionary(y, m):
            return -sum(t.amount_minor for t in led.txns
                        if t.amount_minor < 0 and t.category in ("Dining", "Shopping")
                        and (t.date.year, t.date.month) == (y, m))

        baseline = [discretionary(y, m) for (y, m) in STATEMENT_MONTHS
                    if (y, m) != (2025, 12)]
        ratio = discretionary(2025, 12) / (sum(baseline) / len(baseline))
        assert 1.7 <= ratio <= 2.5  # brief: ≈ 2.1×

    def test_08_large_one_time(self, ledgers):
        (row,) = _events(ledgers[0], "large_one_time")
        assert row.amount_minor == -184000
        assert row.date.strftime("%Y-%m") == "2025-10"

    def test_09_vacation_cluster(self, ledgers):
        rows = _events(ledgers[0], "vacation_cluster")
        assert len(rows) >= 8
        assert all("DEN" in r.description.upper() or "ALASKA" in r.description
                   for r in rows)
        span = max(r.date for r in rows) - min(r.date for r in rows)
        assert span.days <= 8
        assert min(r.date for r in rows).strftime("%Y-%m") == "2026-03"

    def test_10_income_change(self, ledgers):
        led = ledgers[0]
        pays = sorted((t.date, t.amount_minor) for t in led.txns
                      if "PAYROLL" in t.description)
        before = [a for d, a in pays if d < dt.date(2026, 4, 1)]
        after = [a for d, a in pays if d >= dt.date(2026, 4, 1)]
        assert set(before) == {318000}
        assert set(after) == {351000}

    def test_11_loan_payoff(self, ledgers):
        led = ledgers[0]
        payments = [t for t in led.txns
                    if t.account == "ch_loan_5561" and t.amount_minor > 0]
        assert len(payments) == 8
        assert all(t.amount_minor == 41200 for t in payments)
        assert max(t.date for t in payments).strftime("%Y-%m") == "2026-03"
        spec = led.account("ch_loan_5561")
        final = spec.opening_balance_minor + sum(t.amount_minor for t in led.txns
                                                 if t.account == "ch_loan_5561")
        assert final == 0

    def test_12_crypto(self, ledgers):
        led = ledgers[0]
        assert sum(1 for t in led.txns if t.event == "crypto_dca") >= 100
        sale = [t for t in _events(led, "crypto_sale")
                if t.account == "gemini" and t.amount_minor > 0]
        assert sale and sale[0].amount_minor == 936000
        landed = [t for t in _events(led, "crypto_sale")
                  if t.account == "ab_chk_4417"]
        assert landed and landed[0].amount_minor == 920000

    def test_13_date_shifts(self, ledgers):
        rows = _events(ledgers[0], "date_shift")
        assert len(rows) == 3
        for r in rows:
            delta = (r.stmt_date - r.date).days
            assert 1 <= delta <= 3
        assert len({r.account for r in rows}) == 3


class TestGeneratedFiles:
    def test_inventory(self):
        assert len(list((SAMPLE / "jordan").rglob("*.pdf"))) == 79
        assert len(list((SAMPLE / "priya").rglob("*.pdf"))) == 36
        assert len(list(SAMPLE.rglob("*.ofx"))) == 12
        assert len(list(SAMPLE.rglob("*.csv"))) == 26
        assert (SAMPLE / "DATASET_GUIDE.md").exists()
        assert (SAMPLE / "provider_fixtures" / "jordan.json").exists()
        assert (SAMPLE / "provider_fixtures" / "priya.json").exists()

    def test_pdf_extractable_text(self):
        import pdfplumber

        pdf = SAMPLE / "jordan" / "statements" / "american_bank" / \
            "checking_4417_2025-11.pdf"
        with pdfplumber.open(pdf) as doc:
            text = "\n".join(page.extract_text() for page in doc.pages)
        assert "AMERICAN BANK" in text
        assert "4417" in text
        assert "CHECK #1042" in text        # planted event 2 is on this statement
        assert re.search(r"\d+\.\d{2}", text)

    def test_sapphire_december_spans_pages(self):
        import pdfplumber

        pdf = SAMPLE / "jordan" / "statements" / "chase" / \
            "credit_card_1902_2025-12.pdf"
        with pdfplumber.open(pdf) as doc:
            assert len(doc.pages) >= 2

    def test_ofx_parses(self):
        from ofxparse import OfxParser

        path = SAMPLE / "jordan" / "ofx" / "chase_checking_7734_2025-08.ofx"
        with open(path, "rb") as f:
            ofx = OfxParser.parse(f)
        assert ofx.account.number.endswith("7734")
        assert len(ofx.account.statement.transactions) > 10

    def test_venmo_multirow_header(self):
        path = SAMPLE / "jordan" / "exports" / "venmo" / "venmo_statement_2025-08.csv"
        lines = path.read_text().splitlines()
        assert lines[0].startswith("Account Statement")
        assert lines[2].split(",")[1] == "ID"  # real header is on row 3

    def test_provider_fixture_balances_are_integers(self):
        import json

        fixture = json.loads((SAMPLE / "provider_fixtures" / "jordan.json").read_text())
        for account in fixture["accounts"]:
            assert isinstance(account["current_balance_minor"], int)
        for t in fixture["transactions"][:200]:
            assert isinstance(t["amount_minor"], int)
