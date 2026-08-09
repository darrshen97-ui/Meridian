"""Profile 2 — Priya Raman (isolation proof). Chicago, IL.

Deliberately disjoint from Profile 1: different institutions, city, income level,
spending shape, and zero shared merchants. Its only job is to make cross-profile
leakage immediately visible. No planted events, no documents — provider feed only.
"""
from __future__ import annotations

import datetime as dt
import random

from .core import (
    PERIOD_START,
    STATEMENT_MONTHS,
    TODAY,
    AccountSpec,
    Ledger,
    biweekly,
    c,
    month_days,
)

GROCERS = ["MARIANO'S #23 CHICAGO", "JEWEL-OSCO 0113 STATE ST", "H MART CHICAGO IL",
           "PETE'S FRESH MARKET 04"]
DINING = ["GIRL & THE GOAT", "LOU MALNATI'S 11", "WILDBERRY CAFE RANDOLPH",
          "CHIYO RAMEN LAKEVIEW", "AVEC RESTAURANT", "PEQUOD'S PIZZA",
          "DUSEK'S BOARD & BEER"]
SHOPPING = ["ART INSTITUTE SHOP", "UNIQLO MICHIGAN AVE", "SEMICOLON BOOKSTORE",
            "FOXTROT MARKET 08", "CB2 LINCOLN PARK"]


def accounts() -> list[AccountSpec]:
    return [
        AccountSpec("ally_chk_5502", "Ally Bank", "bank", "Ally Interest Checking",
                    "5502", "checking", True, c(4120.00)),
        AccountSpec("ally_sav_7719", "Ally Bank", "bank", "Ally Online Savings",
                    "7719", "savings", True, c(21500.00)),
        AccountSpec("capone_3345", "Capital One", "credit", "Capital One Venture",
                    "3345", "credit_card", False, -c(890.00)),
        AccountSpec("fidelity_0084", "Fidelity", "brokerage", "Fidelity Brokerage",
                    "0084", "investment", False, c(38400.00)),
        AccountSpec("coinbase", "Coinbase", "exchange", "Coinbase (ETH)",
                    None, "crypto", False, c(910.00)),
        AccountSpec("paypal", "PayPal", "payment_app", "PayPal Balance",
                    None, "payment_app", True, c(123.00)),
    ]


def build(rng: random.Random) -> Ledger:
    led = Ledger("priya", "Priya Raman", "priya@meridian.demo",
                 "lakefront-audit-26", accounts())

    # Monthly salary on the 1st.
    for (y, m) in STATEMENT_MONTHS + [(2026, 8)]:
        d = dt.date(y, m, 1)
        if d <= TODAY:
            led.add("ally_chk_5502", d, "LAKESHORE HEALTH SYS PAYROLL", c(6240.00),
                    type="credit", merchant="Lakeshore Health", category="Income")

    for (y, m) in STATEMENT_MONTHS + [(2026, 8)]:
        first, last = month_days(y, m)
        end = min(last, TODAY)

        def day(n: int) -> dt.date:
            return first.replace(day=n)

        def rday() -> dt.date:
            return first.replace(day=rng.randint(1, min(end.day, 28)))

        fixed = [
            (day(1), "ally_chk_5502", "STATE STREET LOFTS RENT", -c(2150.00), "Housing"),
            (day(4), "ally_chk_5502", "COMED ELECTRIC BILL",
             -c(58.00) - c([21, 14, 6, 24, 39, 44, 36, 22, 8, 3, 5, 12][(m - 8) % 12]),
             "Utilities"),
            (day(6), "ally_chk_5502", "PEOPLES GAS CHICAGO",
             -c(28.00) - c([4, 2, 11, 33, 49, 57, 41, 25, 7, 2, 1, 2][(m - 8) % 12]),
             "Utilities"),
            (day(7), "ally_chk_5502", "RCN CHICAGO INTERNET", -c(64.99), "Utilities"),
            (day(10), "ally_chk_5502", "STATE FARM INS 04-BB", -c(94.60), "Insurance"),
            (day(13), "ally_chk_5502", "VERIZON WIRELESS PMT", -c(78.00), "Utilities"),
            (day(2), "ally_chk_5502", "CHICAGO ATHLETIC CLUBS", -c(89.00), "Health"),
        ]
        for when, acct, desc, amount, cat in fixed:
            if when <= TODAY:
                led.add(acct, when, desc, amount, category=cat)

        if day(3) <= TODAY:
            led.add("ally_chk_5502", day(3), "FIDELITY BROKERAGE EFT", -c(500.00),
                    type="transfer", category="Transfers")
            led.add("fidelity_0084", day(3), "EFT RECEIVED - ALLY *5502", c(500.00),
                    type="transfer", category="Transfers")
        if day(16) <= TODAY:
            led.add("ally_chk_5502", day(16), "TRANSFER TO ALLY SAVINGS *7719",
                    -c(750.00), type="transfer", category="Transfers")
            led.add("ally_sav_7719", day(16), "TRANSFER FROM ALLY CHECKING *5502",
                    c(750.00), type="transfer", category="Transfers")
        if end == last:
            led.add("ally_sav_7719", last, "INTEREST PAID", c(38.00) + (m * 11) % 900,
                    type="credit", category="Income")

        # Card spending (Venture) — dining, groceries, transit, shopping.
        def spend(pool, n, lo, hi, cat):
            for _ in range(n):
                desc = rng.choice(pool)
                led.add("capone_3345", rday(), desc, -round(rng.uniform(lo, hi) * 100),
                        merchant=desc.title(), category=cat)

        spend(DINING, 17, 16, 88, "Dining")
        spend(GROCERS, 10, 28, 105, "Groceries")
        spend(SHOPPING, 9, 14, 130, "Shopping")
        spend(["VENTRA CTA FARE", "DIVVY BIKES CHI"], 11, 2.5, 15, "Transport")
        spend(["CINESTREAM MONTHLY", "AUDIOSPHERE PLAN"], 2, 9.99, 16.99, "Subscriptions")

        # Errands on the debit card.
        for _ in range(4):
            desc = rng.choice(["OSCO DRUG 0113 STATE ST", "MARINER PHARMACY LINCOLN PK",
                               "BINNY'S BEVERAGE 12", "MARSHALL'S 0114 STATE ST"])
            led.add("ally_chk_5502", rday(), desc, -round(rng.uniform(8, 60) * 100),
                    merchant=desc.title(), category="Shopping")

        # Card autopay in full on the 21st (previous cycle).
        pay_date = day(21)
        if pay_date <= TODAY:
            prev_y, prev_m = (y, m - 1) if m > 1 else (y - 1, 12)
            owed = -sum(t.amount_minor for t in led.txns
                        if t.account == "capone_3345" and t.amount_minor < 0
                        and (t.date.year, t.date.month) == (prev_y, prev_m))
            owed = owed or c(890.00)  # first cycle pays the opening balance
            led.add("ally_chk_5502", pay_date, "CAPITAL ONE AUTOPAY *3345", -owed,
                    type="transfer", category="Transfers")
            led.add("capone_3345", pay_date, "AUTOPAY PAYMENT RECEIVED", owed,
                    type="credit", category="Transfers")

        # PayPal: online purchases + monthly top-up.
        if day(5) <= TODAY:
            led.add("ally_chk_5502", day(5), "PAYPAL INST XFER", -c(150.00),
                    type="transfer", category="Transfers")
            led.add("paypal", day(5), "TOP UP FROM ALLY *5502", c(150.00),
                    type="transfer", category="Transfers")
        for _ in range(9):
            led.add("paypal", rday(), rng.choice(
                ["PAYPAL *THREADHAUS", "PAYPAL *PLANTPOST", "PAYPAL *INKWELL PRESS",
                 "PAYPAL *MIDWAY CERAMICS", "PAYPAL *WICKER PARK VINTAGE"]),
                -round(rng.uniform(9, 68) * 100), category="Shopping")

    # Coinbase: biweekly ETH DCA with monthly funding.
    for d in biweekly(dt.date(2025, 8, 5), TODAY):
        eth_px = 2_380 + (d.toordinal() * 13) % 800
        led.add("coinbase", d, f"BUY ETH {75_00 / (eth_px * 100):.5f} @ {eth_px:,}",
                -c(75.00), category="Crypto")
    for (y, m) in STATEMENT_MONTHS + [(2026, 8)]:
        d = dt.date(y, m, 4)
        if d <= TODAY:
            led.add("ally_chk_5502", d, "COINBASE INC ACH DEBIT", -c(160.00),
                    type="transfer", category="Crypto")
            led.add("coinbase", d, "ACH DEPOSIT FROM ALLY *5502", c(160.00),
                    type="transfer", category="Crypto")

    for t in led.txns:
        if t.date > dt.date(2026, 7, 31):
            t.in_statement = False
    led.finalize()
    return led
