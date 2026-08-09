"""Profile 1 — Jordan Reyes (primary demo). Portland, OR.

Full institutional breadth plus all 13 planted events from brief §9.
Every planted row carries an `event` tag so the guide and the tests can find it.
"""
from __future__ import annotations

import datetime as dt
import random

from .core import (
    PERIOD_START,
    TODAY,
    AccountSpec,
    Ledger,
    biweekly,
    c,
    mondays_between,
    month_days,
    STATEMENT_MONTHS,
)

CLOSURE_DAY = dt.date(2026, 6, 20)     # *8123 closed after the June compromise
PAYOFF_MONTH = (2026, 3)               # auto loan final payment

GROCERS = ["SAFEWAY #1442 PORTLAND OR", "TRADER JOE'S #145 PORTLAND",
           "WHOLE FOODS MKT PDX", "FRED MEYER 00318 PORTLAND OR"]
DINING = ["OLIVE & VINE RESTAURANT", "PDX THAI KITCHEN", "RAMEN RYU BURNSIDE",
          "LA TAQUERIA ALDER ST", "BRIDGETOWN PIZZA CO", "CASCADE BREWING PUB",
          "NONNA'S TRATTORIA", "SCREEN DOOR PDX", "KACHKA PORTLAND"]
AMBIGUOUS = ["SQ *BLUE STEM", "SQ *RIVER ROAST CO", "SQ *SFT SERVE", "SQ *HXH 22",
             "TST* MERIDIAN 04", "TST* HARLOW PDX", "TST* GRAIN&GRIT",
             "PAYPAL *STGHRSE", "PAYPAL *KKARTS", "PP*DIGIWARE 402-935-7733",
             "POS DEBIT 8871 WDM IA", "CKE*8891 SVC FEE", "IC* INSTACART TIP",
             "VESTA *PDX07", "GPC*4417 SERV"]
SHOPPING = ["POWELL'S BOOKS #1", "REI #87 PORTLAND", "TARGET 00021048",
            "COLUMBIA SPORTSWEAR EMP", "AMZN MKTP US*", "NIKE PORTLAND 014"]
GAS = ["SHELL OIL 57444829", "CHEVRON 0091 PORTLAND", "ARCO#83112 POWELL BLVD"]
DELIVERY = ["GRUBHUB PDXEATS", "DOORDASH*PDX", "UBER *EATS PDX"]
VACATION = [("ALASKA AIR 0272318477", -c(348.40)), ("DENVER MARRIOTT DTWN", -c(689.34)),
            ("SNOOZE AM EATERY DENVER CO", -c(41.85)), ("UBER *TRIP DENVER", -c(23.10)),
            ("REI DENVER CO FLAGSHIP", -c(129.95)), ("MTN GOAT COFFEE DENVER CO", -c(11.40)),
            ("ROOT DOWN DEN AIRPORT", -c(52.60)), ("UBER *TRIP DENVER", -c(19.75)),
            ("DENVER ART MUSEUM", -c(28.00)), ("LITTLE MAN ICE CREAM DEN", -c(14.25))]


def accounts() -> list[AccountSpec]:
    return [
        AccountSpec("ab_chk_4417", "American Bank", "bank", "American Bank Checking",
                    "4417", "checking", True, c(6847.22)),
        AccountSpec("ab_chk_8123", "American Bank", "bank", "American Bank Checking",
                    "8123", "checking", True, c(1412.90),
                    closed_at=CLOSURE_DAY,
                    closed_reason="Closed after suspected card compromise; replaced by *4417"),
        AccountSpec("ab_sav_2290", "American Bank", "bank", "American Bank Savings",
                    "2290", "savings", True, c(12300.00)),
        AccountSpec("ch_chk_7734", "Chase", "bank", "Chase Checking",
                    "7734", "checking", True, c(3208.15)),
        AccountSpec("ch_cc_1902", "Chase", "credit", "Chase Sapphire",
                    "1902", "credit_card", False, -c(1240.55)),
        AccountSpec("disc_6088", "Discover", "credit", "Discover It Card",
                    "6088", "credit_card", False, -c(312.40)),
        AccountSpec("ch_loan_5561", "Chase", "loan", "Chase Auto Loan",
                    "5561", "loan", False, -c(3296.00),
                    closed_at=dt.date(2026, 3, 18), closed_reason="Paid in full"),
        AccountSpec("venmo", "Venmo", "payment_app", "Venmo Balance",
                    None, "payment_app", True, c(86.10)),
        AccountSpec("cashapp", "Cash App", "payment_app", "Cash App Balance",
                    None, "payment_app", True, c(45.75)),
        AccountSpec("binance", "Binance", "exchange", "Binance (BTC, ETH)",
                    None, "crypto", False, c(1220.00)),
        AccountSpec("gemini", "Gemini", "exchange", "Gemini (BTC, SOL)",
                    None, "crypto", False, c(684.00)),
    ]


def build(rng: random.Random) -> Ledger:
    led = Ledger("jordan", "Jordan Reyes", "jordan@meridian.demo",
                 "rowhouse-ledger-26", accounts())

    _income(led)
    _fixed_bills(led)
    _spending(led, rng)
    _payment_apps(led, rng)
    _crypto(led, rng)
    _card_payments(led)
    _compromise_and_closure(led)
    _date_shifts(led)
    _tail_flags(led)
    led.finalize()
    return led


# -- Income (planted event 10: biweekly net rises Apr 2026) --------------------

def _income(led: Ledger) -> None:
    for d in biweekly(dt.date(2025, 8, 8), TODAY):
        amount = c(3510.00) if d >= dt.date(2026, 4, 1) else c(3180.00)
        first_raised = dt.date(2026, 4, 1) <= d < dt.date(2026, 4, 15)
        led.add("ab_chk_4417", d, "NORTHRIVER ANALYTICS PAYROLL PPD", amount,
                type="credit", merchant="Northriver Analytics", category="Income",
                event="income_change" if first_raised else "")


def _fixed_bills(led: Ledger) -> None:
    for (y, m) in STATEMENT_MONTHS + [(2026, 8)]:
        first, last = month_days(y, m)

        def day(n: int) -> dt.date:
            return first.replace(day=n)

        def in_tail(d: dt.date) -> bool:
            return d > TODAY

        rows = [
            (day(1), "ab_chk_4417", "WILLAMETTE PROPERTY MGMT RENT", -c(1650.00),
             "Willamette Property Mgmt", "Housing"),
            (day(2), "ab_chk_4417", "IRONWORKS GYM MONTHLY", -c(34.00),
             "Ironworks Gym", "Health"),
            (day(3), "ab_chk_4417", "COMCAST XFINITY INTERNET", -c(79.99),
             "Comcast", "Utilities"),
            (day(5), "ab_chk_4417", "GEICO AUTO INSURANCE", -c(128.40),
             "GEICO", "Insurance"),
            (day(9), "ab_chk_4417", "LEMONADE RENTERS INS", -c(18.25),
             "Lemonade", "Insurance"),
            (day(12), "ab_chk_4417", "PORTLAND GENERAL ELECTRIC",
             -c(72.00) - c([38, 26, 9, 41, 63, 71, 58, 33, 12, 4, 8, 19][(m - 8) % 12]),
             "Portland General Electric", "Utilities"),
            (day(17), "ab_chk_4417", "T-MOBILE PCS SVC", -c(65.00),
             "T-Mobile", "Utilities"),
            (day(20), "ab_chk_4417", "NW NATURAL GAS BILL",
             -c(24.00) - c([6, 2, 14, 39, 55, 61, 44, 27, 9, 3, 1, 2][(m - 8) % 12]),
             "NW Natural", "Utilities"),
        ]
        for when, acct, desc, amount, merchant, cat in rows:
            if not in_tail(when):
                led.add(acct, when, desc, amount, merchant=merchant, category=cat)

        if not in_tail(day(15)):
            led.add("ab_chk_4417", day(15), "ONLINE TRANSFER TO SAVINGS *2290",
                    -c(400.00), type="transfer", category="Transfers")
            led.add("ab_sav_2290", day(15), "ONLINE TRANSFER FROM CHECKING *4417",
                    c(400.00), type="transfer", category="Transfers")
        if not in_tail(last):
            led.add("ab_sav_2290", last, "INTEREST PAYMENT",
                    c(9.00) + (m * 7) % 400, type="credit", category="Income")

        # Funding transfers to the secondary checking (until closure) and Chase checking.
        if not in_tail(day(1)) and day(1) <= CLOSURE_DAY.replace(day=1):
            if (y, m) <= (2026, 6):
                led.add("ab_chk_4417", day(1), "ONLINE TRANSFER TO CHECKING *8123",
                        -c(800.00), type="transfer", category="Transfers")
                led.add("ab_chk_8123", day(1), "ONLINE TRANSFER FROM CHECKING *4417",
                        c(800.00), type="transfer", category="Transfers")
        if not in_tail(day(2)):
            led.add("ab_chk_4417", day(2), "ACH TRANSFER TO CHASE *7734",
                    -c(700.00), type="transfer", category="Transfers")
            led.add("ch_chk_7734", day(2), "ONLINE TRANSFER FROM AMERICAN BK",
                    c(700.00), type="transfer", category="Transfers")

        # Auto loan (planted event 11: the $412 payment stops after March 2026).
        if (y, m) <= PAYOFF_MONTH and not in_tail(day(6)):
            led.add("ab_chk_4417", day(6), "CHASE AUTO LOAN PAYMENT *5561",
                    -c(412.00), category="Loan Payments",
                    event="loan_payoff" if (y, m) == PAYOFF_MONTH else "")
            led.add("ch_loan_5561", day(6), "PAYMENT RECEIVED - THANK YOU",
                    c(412.00), type="credit", category="Loan Payments",
                    event="loan_payoff" if (y, m) == PAYOFF_MONTH else "")


# -- Discretionary spending ----------------------------------------------------

def _spend_month(led: Ledger, rng: random.Random, y: int, m: int) -> None:
    first, last = month_days(y, m)
    end = min(last, TODAY)
    dec_spike = 2.1 if (y, m) == (2025, 12) else 1.0  # planted event 7

    def rday(lo: int = 1) -> dt.date:
        return first.replace(day=rng.randint(lo, min(end.day, 28)))

    def spend(acct: str, pool: list[str], n: int, lo: float, hi: float, cat: str,
              factor: float = 1.0) -> None:
        for _ in range(round(n * (dec_spike if cat in ("Dining", "Shopping") else 1.0))):
            d = rday()
            if acct == "ab_chk_8123" and d >= CLOSURE_DAY:
                acct2 = "ab_chk_4417"  # planted event 5: replacement resumes on *4417
            else:
                acct2 = acct
            amount = -round(rng.uniform(lo, hi) * factor * 100)
            desc = rng.choice(pool)
            led.add(acct2, d, desc, amount, category=cat,
                    merchant=None if desc in AMBIGUOUS else desc.title())

    # Secondary checking: groceries + coffee (ambiguous descriptors → review queue).
    spend("ab_chk_8123", GROCERS, 7, 32, 118, "Groceries")
    spend("ab_chk_8123", AMBIGUOUS, 12, 4.25, 16.5, "Dining")
    # Primary checking: pharmacy and errands.
    spend("ab_chk_4417", ["WALGREENS #0662 PORTLAND", "CVS/PHARMACY 09915",
                          "USPS PO 9701 BOX", "PETCO 1042 PDX"], 4, 6, 54, "Shopping")
    # Chase checking: delivery, rides, transit, online.
    spend("ch_chk_7734", DELIVERY, 6, 21, 48, "Dining")
    spend("ch_chk_7734", ["UBER *TRIP", "LYFT *RIDE PDX"], 9, 9, 27, "Transport")
    spend("ch_chk_7734", ["TRIMET TVM PORTLAND"], 4, 2.8, 5.6, "Transport")
    spend("ch_chk_7734", ["AMZN MKTP US*", "EBAY O*"], 8, 12, 88, "Shopping")
    # Sapphire: dining, coffee, gas, shopping, subscriptions below.
    spend("ch_cc_1902", DINING, 21, 17, 96, "Dining")
    spend("ch_cc_1902", AMBIGUOUS, 8, 5.5, 18, "Dining")
    spend("ch_cc_1902", GAS, 3, 36, 63, "Transport")
    spend("ch_cc_1902", SHOPPING, 6, 18, 140, "Shopping")
    # Discover: groceries, online, big-box.
    spend("disc_6088", GROCERS[2:] + ["NEW SEASONS MARKET 09"], 7, 24, 92, "Groceries")
    spend("disc_6088", ["AMZN MKTP US*", "ETSY.COM*", "STEAMGAMES.COM 425"], 7, 9, 74, "Shopping")
    spend("disc_6088", ["TARGET 00021048", "COSTCO WHSE #0692"], 2, 38, 176, "Shopping")

    # Subscriptions on Sapphire (planted event 4: StreamMax 15.99 → 22.99 in Jan 2026).
    streammax = c(22.99) if (y, m) >= (2026, 1) else c(15.99)
    if first.replace(day=8) <= TODAY:
        led.add("ch_cc_1902", first.replace(day=8), "STREAMMAX.COM SUBSCR", -streammax,
                merchant="StreamMax", category="Subscriptions",
                event="subscription_increase" if (y, m) in ((2025, 12), (2026, 1)) else "")
    if first.replace(day=11) <= TODAY:
        led.add("ch_cc_1902", first.replace(day=11), "MELODIFY PREMIUM", -c(10.99),
                merchant="Melodify", category="Subscriptions")
    if first.replace(day=19) <= TODAY:
        led.add("ch_cc_1902", first.replace(day=19), "CLOUDBOX STORAGE 2TB", -c(2.99),
                merchant="Cloudbox", category="Subscriptions")


def _spending(led: Ledger, rng: random.Random) -> None:
    for (y, m) in STATEMENT_MONTHS + [(2026, 8)]:
        _spend_month(led, rng, y, m)

    # Planted event 8: one-time $1,840 transmission repair (Oct 2025, Sapphire).
    led.add("ch_cc_1902", dt.date(2025, 10, 14), "PRECISION AUTO TRANSMISSION",
            -c(1840.00), merchant="Precision Auto", category="Transport",
            event="large_one_time")

    # Planted event 9: vacation cluster — one week in Denver, CO (Mar 14-21, 2026).
    for i, (desc, amount) in enumerate(VACATION):
        led.add("ch_cc_1902", dt.date(2026, 3, 14) + dt.timedelta(days=i % 8),
                desc, amount, category="Travel", event="vacation_cluster")

    # Planted event 1: duplicate charge — same merchant/amount, 2 days apart (Feb 2026).
    for d in (dt.date(2026, 2, 12), dt.date(2026, 2, 14)):
        led.add("ch_cc_1902", d, "OLIVE & VINE RESTAURANT", -c(86.40),
                merchant="Olive & Vine", category="Dining", event="duplicate_charge")

    # Planted event 2: on the statement, missing from the provider feed (Nov 2025).
    led.add("ab_chk_4417", dt.date(2025, 11, 18), "CHECK #1042", -c(230.00),
            category="Cash", in_provider=False, event="missing_in_provider")

    # Planted event 3: pending in the provider feed, never on any statement (Mar 2026).
    led.add("disc_6088", dt.date(2026, 3, 9), "CONOCO PREAUTH HOLD 00814",
            -c(75.00), category="Transport", in_statement=False, pending=True,
            event="never_cleared_pending")


def _payment_apps(led: Ledger, rng: random.Random) -> None:
    friends_out = ["VENMO PAYMENT - SAM K", "VENMO PAYMENT - RILEY M",
                   "VENMO PAYMENT - PDX CLIMBING CLUB", "VENMO PAYMENT - DANA W"]
    friends_in = ["VENMO FROM ALEX R", "VENMO FROM PRI T"]
    for (y, m) in STATEMENT_MONTHS + [(2026, 8)]:
        first, last = month_days(y, m)
        end = min(last, TODAY)

        def rday() -> dt.date:
            return first.replace(day=rng.randint(1, min(end.day, 28)))

        if first.replace(day=8) <= TODAY:
            led.add("ab_chk_4417", first.replace(day=8), "VENMO CASHOUT FUNDING",
                    -c(120.00), type="transfer", category="Transfers")
            led.add("venmo", first.replace(day=8), "TRANSFER FROM AMERICAN BANK *4417",
                    c(120.00), type="transfer", category="Transfers")
        if first.replace(day=11) <= TODAY:
            led.add("ab_chk_4417", first.replace(day=11), "CASH APP*ADD CASH",
                    -c(100.00), type="transfer", category="Transfers")
            led.add("cashapp", first.replace(day=11), "ADD CASH FROM *4417",
                    c(100.00), type="transfer", category="Transfers")
        for _ in range(9):
            led.add("venmo", rday(), rng.choice(friends_out),
                    -round(rng.uniform(8, 62) * 100), category="Transfers")
        for _ in range(2):
            led.add("venmo", rday(), rng.choice(friends_in),
                    round(rng.uniform(12, 80) * 100), type="credit", category="Transfers")
        for _ in range(6):
            led.add("cashapp", rday(), rng.choice(
                ["CASH APP PAY - FOOD CARTS PDX", "CASH APP PAY - BARBER 12TH AVE",
                 "CASH APP PAY - VINYL FAIR", "CASH APP PAY - N MISSISSIPPI MKT"]),
                -round(rng.uniform(6, 45) * 100), category="Shopping")
        led.add("cashapp", rday(), "CASH APP RECEIVED - J. DOE",
                round(rng.uniform(10, 40) * 100), type="credit", category="Transfers")

        # One ATM withdrawal a month.
        led.add("ab_chk_4417", rday(), "ATM WITHDRAWAL AB 5TH & MAIN",
                -rng.choice([c(60), c(80), c(100), c(140)]), category="Cash")


def _crypto(led: Ledger, rng: random.Random) -> None:
    """Weekly DCA buys throughout (event 12), one large partial sale May 2026."""
    for d in mondays_between(PERIOD_START, TODAY):
        btc_px = 58_000 + (d.toordinal() * 37) % 14_000
        eth_px = 2_400 + (d.toordinal() * 17) % 900
        sol_px = 130 + (d.toordinal() * 7) % 60
        led.add("binance", d, f"BUY BTC {40_00 / (btc_px * 100):.6f} @ {btc_px:,}",
                -c(40.00), category="Crypto", event="crypto_dca")
        led.add("binance", d, f"BUY ETH {25_00 / (eth_px * 100):.5f} @ {eth_px:,}",
                -c(25.00), category="Crypto", event="crypto_dca")
        led.add("gemini", d, f"BUY SOL {25_00 / (sol_px * 100):.4f} @ {sol_px}",
                -c(25.00), category="Crypto", event="crypto_dca")
    for (y, m) in STATEMENT_MONTHS + [(2026, 8)]:
        first, _ = month_days(y, m)
        if first <= TODAY:
            led.add("ab_chk_4417", first, "ACH BINANCE US FUNDING", -c(300.00),
                    type="transfer", category="Crypto")
            led.add("binance", first, "ACH DEPOSIT FROM AMERICAN BANK *4417",
                    c(300.00), type="transfer", category="Crypto")
            led.add("ab_chk_4417", first, "ACH GEMINI TRUST FUNDING", -c(110.00),
                    type="transfer", category="Crypto")
            led.add("gemini", first, "ACH DEPOSIT FROM AMERICAN BANK *4417",
                    c(110.00), type="transfer", category="Crypto")

    # Planted event 12 (sale leg): partial BTC sale on Gemini, proceeds to checking.
    led.add("gemini", dt.date(2026, 5, 12), "SELL BTC 0.150000 @ 62,400",
            c(9360.00), type="credit", category="Crypto", event="crypto_sale")
    led.add("gemini", dt.date(2026, 5, 14), "WITHDRAWAL TO AMERICAN BANK *4417",
            -c(9200.00), type="transfer", category="Crypto", event="crypto_sale")
    led.add("ab_chk_4417", dt.date(2026, 5, 14), "GEMINI TRUST CO ACH CREDIT",
            c(9200.00), type="transfer", category="Crypto", event="crypto_sale")


def _card_payments(led: Ledger) -> None:
    """Pay each card's prior-cycle purchases in full from *4417."""
    for card, payday, first_amount in (
        ("ch_cc_1902", 25, c(1240.55)),
        ("disc_6088", 27, c(312.40)),
    ):
        prior = first_amount
        for (y, m) in STATEMENT_MONTHS + [(2026, 8)]:
            pay_date = dt.date(y, m, payday)
            if pay_date > TODAY:
                break
            if prior > 0:
                led.add("ab_chk_4417", pay_date,
                        f"PAYMENT TO {'CHASE CARD' if card == 'ch_cc_1902' else 'DISCOVER'} "
                        f"*{led.account(card).mask}", -prior,
                        type="transfer", category="Transfers")
                led.add(card, pay_date, "PAYMENT RECEIVED - THANK YOU", prior,
                        type="credit", category="Transfers")
            prior = -sum(
                t.amount_minor for t in led.txns
                if t.account == card and t.amount_minor < 0 and not t.pending
                and t.date.year == y and t.date.month == m
            )


def _compromise_and_closure(led: Ledger) -> None:
    """Planted event 5: three out-of-pattern foreign charges over 36 hours, June 2026."""
    fraud = [
        (dt.date(2026, 6, 14), "LOJA ELETRONICA LISBOA PT", -c(312.55)),
        (dt.date(2026, 6, 15), "TVDE TAXI LISBOA PT", -c(48.20)),
        (dt.date(2026, 6, 16), "CAMBIO ATM WD LISBOA PT", -c(203.77)),
    ]
    for d, desc, amount in fraud:
        led.add("ab_chk_8123", d, desc, amount, category="Uncategorized",
                event="card_compromise")

    # Close the account: remaining balance moves to *4417 on the closure day.
    residual = led.account("ab_chk_8123").opening_balance_minor + sum(
        t.amount_minor for t in led.txns
        if t.account == "ab_chk_8123" and not t.pending
    )
    led.add("ab_chk_8123", CLOSURE_DAY, "ACCOUNT CLOSURE - BALANCE TO *4417",
            -residual, type="transfer", category="Transfers", event="card_compromise")
    led.add("ab_chk_4417", CLOSURE_DAY, "BALANCE TRANSFER FROM CLOSED *8123",
            residual, type="transfer", category="Transfers", event="card_compromise")


def _date_shifts(led: Ledger) -> None:
    """Planted event 13: statement date differs from provider date by 1-3 days."""
    targets = [
        ("ch_cc_1902", dt.date(2025, 9, 1), dt.date(2025, 9, 25), 2),
        ("ab_chk_4417", dt.date(2026, 1, 1), dt.date(2026, 1, 25), 3),
        ("disc_6088", dt.date(2026, 5, 1), dt.date(2026, 5, 24), 1),
    ]
    for account, lo, hi, shift in targets:
        candidates = [t for t in led.txns
                      if t.account == account and lo <= t.date <= hi
                      and not t.event and t.in_statement and t.in_provider
                      and not t.pending and t.type == "debit"]
        t = candidates[len(candidates) // 2]
        t.statement_date = t.date + dt.timedelta(days=shift)
        t.event = "date_shift"


def _tail_flags(led: Ledger) -> None:
    """Aug 1-9 2026 exists only in the provider feed — no statement covers it."""
    for t in led.txns:
        if t.date > dt.date(2026, 7, 31):
            t.in_statement = False
