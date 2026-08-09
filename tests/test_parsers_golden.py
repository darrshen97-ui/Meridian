"""Milestone 5 checkpoint part 1 — golden-file tests.

Every generated sample document must parse, and the parsed rows must agree with
the generator's canonical ledger: same count, same dates, same signed amounts.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from mockgen.core import STATEMENT_MONTHS  # noqa: E402
from mockgen.output import build_ledgers, statement_months_for, PDF_ACCOUNTS  # noqa: E402

from app.parsers import find_parser  # noqa: E402

SAMPLE = PROJECT_ROOT / "sample_data"


@pytest.fixture(scope="module")
def jordan():
    led, _ = build_ledgers()
    return led


def _parse(path: Path):
    content = path.read_bytes()
    parser = find_parser(path.name, content)
    assert parser is not None, f"no parser matched {path.name}"
    return parser.parse(path.name, content)


def _pdf_paths():
    return sorted(SAMPLE.rglob("*.pdf"))


def test_every_document_has_a_parser_and_parses():
    docs = [p for p in SAMPLE.rglob("*")
            if p.suffix.lower() in (".pdf", ".csv", ".ofx")]
    assert len(docs) == 117
    for path in docs:
        parsed = _parse(path)
        assert parsed.problems == [], f"{path.name}: {parsed.problems[:2]}"
        assert parsed.transactions, f"{path.name}: zero transactions"


@pytest.mark.parametrize("path", _pdf_paths(), ids=lambda p: p.name)
def test_pdf_statements_match_ledger_exactly(path, jordan):
    account_key = {
        "checking_4417": "ab_chk_4417", "checking_8123": "ab_chk_8123",
        "savings_2290": "ab_sav_2290", "checking_7734": "ch_chk_7734",
        "credit_card_1902": "ch_cc_1902", "credit_card_6088": "disc_6088",
        "loan_5561": "ch_loan_5561",
    }[path.stem.rsplit("_", 1)[0]]
    year, month = map(int, path.stem.rsplit("_", 1)[1].split("-"))

    expected = jordan.statement_txns(account_key, year, month)
    parsed = _parse(path)

    assert len(parsed.transactions) == len(expected), path.name
    for got, want in zip(parsed.transactions, expected):
        assert got.posted_date == want.stmt_date, path.name
        assert got.amount_minor == want.amount_minor, \
            f"{path.name}: {got.description} {got.amount_minor} != {want.amount_minor}"
        assert got.description == want.description[:60].strip() or \
            want.description.startswith(got.description), path.name

    # Balances: the summary block must agree with the running ledger.
    first = expected[0].stmt_date.replace(day=1)
    begin = jordan.balance_before(account_key, first)
    end = begin + sum(t.amount_minor for t in expected)
    assert parsed.opening_balance_minor == begin, path.name
    assert parsed.closing_balance_minor == end, path.name

    # The statement identifies its account.
    spec = jordan.account(account_key)
    assert parsed.account.mask == spec.mask, path.name


def test_pdf_statement_counts_per_account(jordan):
    for key in PDF_ACCOUNTS:
        months = statement_months_for(jordan, key)
        spec = jordan.account(key)
        folder = SAMPLE / "jordan" / "statements" / \
            spec.institution.lower().replace(" ", "_")
        got = len(list(folder.glob(f"{spec.type}_{spec.mask}_*.pdf")))
        assert got == len(months), key


def test_ofx_matches_ledger(jordan):
    for (y, m) in STATEMENT_MONTHS:
        path = SAMPLE / "jordan" / "ofx" / f"chase_checking_7734_{y}-{m:02d}.ofx"
        parsed = _parse(path)
        expected = jordan.statement_txns("ch_chk_7734", y, m)
        assert len(parsed.transactions) == len(expected), path.name
        assert parsed.account.mask == "7734"
        got_ids = {t.external_id for t in parsed.transactions}
        want_ids = {t.external_id for t in expected}
        assert got_ids == want_ids, path.name
        assert sum(t.amount_minor for t in parsed.transactions) == \
            sum(t.amount_minor for t in expected), path.name


def test_venmo_and_cashapp_match_ledger(jordan):
    for account, folder, prefix in (
        ("venmo", "venmo", "venmo_statement"),
        ("cashapp", "cash_app", "cash_app_report"),
    ):
        for (y, m) in STATEMENT_MONTHS:
            path = SAMPLE / "jordan" / "exports" / folder / f"{prefix}_{y}-{m:02d}.csv"
            parsed = _parse(path)
            expected = jordan.statement_txns(account, y, m)
            assert len(parsed.transactions) == len(expected), path.name
            assert sorted(t.amount_minor for t in parsed.transactions) == \
                sorted(t.amount_minor for t in expected), path.name


def test_crypto_exports_match_ledger(jordan):
    binance = _parse(SAMPLE / "jordan" / "exports" / "binance" /
                     "binance_trades_2025-08-01_2026-07-31.csv")
    expected_buys = [t for t in jordan.txns
                     if t.account == "binance" and t.description.startswith("BUY ")
                     and t.in_statement]
    assert len(binance.transactions) == len(expected_buys)
    assert all(t.amount_minor < 0 for t in binance.transactions)

    gemini = _parse(SAMPLE / "jordan" / "exports" / "gemini" /
                    "gemini_transaction_history_2025-08-01_2026-07-31.csv")
    expected_trades = [t for t in jordan.txns
                       if t.account == "gemini" and t.in_statement
                       and t.description.startswith(("BUY ", "SELL "))]
    assert len(gemini.transactions) == len(expected_trades)
    assert gemini.notes  # the skipped-transfers note is present
    sale = [t for t in gemini.transactions if t.amount_minor > 0]
    assert len(sale) == 1 and sale[0].amount_minor == 936000

    # Trade descriptions round-trip exactly, so cross-source dedupe can hash-match.
    got = sorted((t.posted_date, t.description) for t in gemini.transactions)
    want = sorted((t.stmt_date, t.description) for t in expected_trades)
    assert got == want
