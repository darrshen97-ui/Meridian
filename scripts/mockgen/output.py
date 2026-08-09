"""Provider fixtures, dataset guide, manifest, and overall orchestration."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from . import jordan, priya
from .core import Ledger, SEED, STATEMENT_MONTHS, TODAY, fmt_money
from .render_csv import render_all_csv
from .render_ofx import render_all_ofx
from .render_pdf import render_statement

PDF_ACCOUNTS = ["ab_chk_4417", "ab_chk_8123", "ab_sav_2290",
                "ch_chk_7734", "ch_cc_1902", "disc_6088", "ch_loan_5561"]


def build_ledgers() -> tuple[Ledger, Ledger]:
    rng = random.Random(SEED)
    led_j = jordan.build(random.Random(rng.random()))
    led_p = priya.build(random.Random(rng.random()))
    return led_j, led_p


def statement_months_for(led: Ledger, key: str) -> list[tuple[int, int]]:
    spec = led.account(key)
    months = STATEMENT_MONTHS
    if spec.closed_at:
        months = [(y, m) for (y, m) in months
                  if (y, m) <= (spec.closed_at.year, spec.closed_at.month)]
    return months


def write_pdfs(out_dir: Path, led: Ledger) -> list[str]:
    written = []
    for key in PDF_ACCOUNTS:
        spec = led.account(key)
        folder = out_dir / "jordan" / "statements" / \
            spec.institution.lower().replace(" ", "_")
        folder.mkdir(parents=True, exist_ok=True)
        slug = f"{spec.type}_{spec.mask}"
        for (y, m) in statement_months_for(led, key):
            p = folder / f"{slug}_{y}-{m:02d}.pdf"
            render_statement(str(p), led, spec, y, m)
            written.append(str(p))
    return written


def write_provider_fixture(out_dir: Path, led: Ledger) -> str:
    institutions: dict[str, dict] = {}
    for a in led.accounts:
        institutions.setdefault(a.institution, {
            "name": a.institution,
            "kind": a.institution_kind,
            "status": "closed" if all(
                x.closed_at for x in led.accounts if x.institution == a.institution
            ) else "active",
        })

    accounts = []
    for a in led.accounts:
        balance = a.opening_balance_minor + sum(
            t.amount_minor for t in led.provider_txns(a.key) if not t.pending
        )
        accounts.append({
            "key": a.key,
            "institution": a.institution,
            "display_name": a.display_name,
            "mask": a.mask,
            "type": a.type,
            "currency": a.currency,
            "is_liquid": a.is_liquid,
            "opening_balance_minor": a.opening_balance_minor,
            "current_balance_minor": balance,
            "closed_at": a.closed_at.isoformat() if a.closed_at else None,
            "closed_reason": a.closed_reason,
        })

    txns = [{
        "account": t.account,
        "date": t.date.isoformat(),
        "description": t.description,
        "amount_minor": t.amount_minor,
        "type": t.type,
        "pending": t.pending,
        "external_id": t.external_id,
        "merchant": t.merchant,
    } for t in led.provider_txns()]

    fixture = {
        "profile": {"key": led.profile_key, "display_name": led.display_name,
                    "email": led.email},
        "as_of": TODAY.isoformat(),
        "institutions": list(institutions.values()),
        "accounts": accounts,
        "transactions": txns,
    }
    out = out_dir / "provider_fixtures"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{led.profile_key}.json"
    path.write_text(json.dumps(fixture, indent=1))
    return str(path)


def _event_rows(led: Ledger, tag: str):
    return [t for t in led.txns if t.event == tag]


def write_guide(out_dir: Path, led_j: Ledger, led_p: Ledger,
                inventory: dict[str, int]) -> str:
    j = led_j

    def li(rows, fmtr):
        return "\n".join(f"   - {fmtr(t)}" for t in rows)

    dup = _event_rows(j, "duplicate_charge")
    missing = _event_rows(j, "missing_in_provider")[0]
    pending = _event_rows(j, "never_cleared_pending")[0]
    fraud = [t for t in _event_rows(j, "card_compromise") if t.type == "debit"]
    big = _event_rows(j, "large_one_time")[0]
    vac = _event_rows(j, "vacation_cluster")
    income = _event_rows(j, "income_change")[0]
    sale = [t for t in _event_rows(j, "crypto_sale") if t.account == "gemini"
            and t.amount_minor > 0][0]
    shifts = _event_rows(j, "date_shift")
    ambiguous_count = sum(1 for t in j.txns if t.description in jordan.AMBIGUOUS)

    dec_dining = -sum(t.amount_minor for t in j.txns
                      if t.category in ("Dining", "Shopping") and t.amount_minor < 0
                      and (t.date.year, t.date.month) == (2025, 12))
    base_dining = [-sum(t.amount_minor for t in j.txns
                        if t.category in ("Dining", "Shopping") and t.amount_minor < 0
                        and (t.date.year, t.date.month) == (y, m))
                   for (y, m) in STATEMENT_MONTHS if (y, m) != (2025, 12)]
    spike_ratio = dec_dining / (sum(base_dining) / len(base_dining))

    guide = f"""# Dataset Guide — Meridian Financial sample data

Generated by `scripts/generate_mock_data.py` with fixed seed `{SEED}` and pinned
reference date **{TODAY}**. Regeneration is byte-identical.

## Demo profiles

| Profile | Email | Password | Transactions |
|---|---|---|---|
| {led_j.display_name} (primary demo) | `{led_j.email}` | `{led_j.password}` | {len(led_j.txns):,} |
| {led_p.display_name} (isolation proof) | `{led_p.email}` | `{led_p.password}` | {len(led_p.txns):,} |

The two profiles share **zero** merchants, institutions, and cities by construction.

## Period and conventions

- Statements cover **Aug 1, 2025 – Jul 31, 2026** (12 calendar months).
- **Aug 1–9, 2026 exists only in the provider feed** — statements lag reality by design;
  this gap makes reconciliation demonstrable.
- Amounts are integer minor units in fixtures; negative = money out of the account.
- Credit-card PDF statements print purchases as positive numbers (industry convention) —
  parsers must normalize signs per institution.
- The PDF layouts differ deliberately per institution (column order, date formats
  `08/15/25` vs `Aug 15, 2025` vs `08/15/2025`); Chase Sapphire's December statement
  spans a page break.

## Document inventory

| Kind | Count |
|---|---|
| PDF bank/card statements | {inventory['pdf_bank']} |
| PDF auto-loan statements | {inventory['pdf_loan']} |
| Venmo CSV (monthly, multi-row header) | 12 |
| Cash App CSV (monthly) | 12 |
| Binance CSV (annual, UTC timestamps) | 1 |
| Gemini CSV (annual, separate fee column) | 1 |
| Chase checking OFX (monthly) | 12 |

Chase checking ••7734 appears in **both** PDF and OFX form on purpose — importing both
must collapse to single transactions via dedupe (DECISIONS.md D-002).

## The 13 planted events (verify the app catches every one)

1. **Duplicate charge** — {dup[0].description}, ${fmt_money(-dup[0].amount_minor)} on
   {dup[0].date} and {dup[1].date} (Chase Sapphire ••1902). Reconciliation should flag
   `duplicate_suspected`.
2. **Missing in provider** — "{missing.description}" ${fmt_money(-missing.amount_minor)}
   on {missing.date}, American Bank ••4417: on the statement, absent from the API feed.
3. **Never-cleared pending** — "{pending.description}" ${fmt_money(-pending.amount_minor)}
   on {pending.date}, Discover ••6088: pending in the provider feed, on no statement.
4. **Subscription price increase** — STREAMMAX.COM $15.99 → $22.99 starting 2026-01-08
   (Chase Sapphire).
5. **Card compromise** — {len(fraud)} foreign charges over 36h on American Bank ••8123:
{li(fraud, lambda t: f'{t.date} · {t.description} · ${fmt_money(-t.amount_minor)}')}
   Account closed {j.account('ab_chk_8123').closed_at}; recurring activity resumes on ••4417.
6. **Ambiguous merchant descriptors** — {ambiguous_count} transactions using descriptors
   like `SQ *BLUE STEM`, `TST* MERIDIAN 04`, `PAYPAL *STGHRSE`, `POS DEBIT 8871 WDM IA`.
   These must land in the review queue with low confidence.
7. **Seasonal spike** — December 2025 discretionary spending is **{spike_ratio:.1f}×**
   the other months' baseline.
8. **One-time large expense** — "{big.description}" ${fmt_money(-big.amount_minor)} on
   {big.date} (Chase Sapphire).
9. **Vacation cluster** — {len(vac)} Denver, CO charges {min(t.date for t in vac)} –
   {max(t.date for t in vac)} (Chase Sapphire).
10. **Income change** — biweekly net $3,180.00 → $3,510.00; first raised deposit
    {income.date}.
11. **Auto loan payoff** — final $412.00 payment {_event_rows(j, 'loan_payoff')[0].date};
    the recurring payment stops after March 2026. 8 loan statements exist.
12. **Crypto activity** — {sum(1 for t in j.txns if t.event == 'crypto_dca')} weekly DCA
    buys across Binance/Gemini; large partial sale "{sale.description}"
    (+${fmt_money(sale.amount_minor)}) on {sale.date}, proceeds withdrawn to ••4417.
13. **Date shifts** — three transactions whose statement date differs from the provider
    date by 1–3 days (reconciliation must match them, not flag them):
{li(shifts, lambda t: f'{t.account} · "{t.description}" · provider {t.date} vs statement {t.stmt_date}')}

## Provider fixtures

`provider_fixtures/jordan.json` and `provider_fixtures/priya.json` are the mock
provider's source of truth (accounts, balances, and the provider-side transaction feed,
including the Aug 1–9 tail and the divergences above).
"""
    path = out_dir / "DATASET_GUIDE.md"
    path.write_text(guide)
    return str(path)


def write_manifest(out_dir: Path) -> None:
    entries = {}
    for p in sorted(out_dir.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            entries[str(p.relative_to(out_dir))] = hashlib.sha256(
                p.read_bytes()).hexdigest()
    (out_dir / "manifest.json").write_text(json.dumps(entries, indent=1))


def generate(out_dir: Path) -> dict:
    from reportlab import rl_config
    rl_config.invariant = 1  # deterministic PDFs: fixed timestamps, no random IDs

    led_j, led_p = build_ledgers()
    pdfs = write_pdfs(out_dir, led_j)
    csvs = render_all_csv(out_dir, led_j)
    ofx = render_all_ofx(out_dir, led_j)
    write_provider_fixture(out_dir, led_j)
    write_provider_fixture(out_dir, led_p)

    inventory = {
        "pdf_bank": sum(1 for p in pdfs if "loan" not in p),
        "pdf_loan": sum(1 for p in pdfs if "loan" in p),
        "csv": len(csvs),
        "ofx": len(ofx),
    }
    write_guide(out_dir, led_j, led_p, inventory)
    write_manifest(out_dir)
    return {
        "jordan_txns": len(led_j.txns),
        "priya_txns": len(led_p.txns),
        **inventory,
    }
