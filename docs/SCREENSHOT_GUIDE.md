# Screenshot Guide — assignment evidence

The assignment requires two screenshots, **each with the system date and time visible**.
The reliable way to satisfy that on Windows is to capture the full screen including the
taskbar, and click the taskbar clock first so the flyout shows the full date.

## Before you start (once)

1. Extract `dist/MeridianFinancial-v0.1.zip` (or use the repo) and double-click
   **`Start Meridian.bat`**. Wait for "Meridian is running at http://127.0.0.1:8787".
2. Sign in as **Jordan Reyes** (`jordan@meridian.demo` / `rowhouse-ledger-26`).
3. Windows: make sure the taskbar clock is visible (Settings → Personalization →
   Taskbar). Capture with **Win + PrtScn** (saves to Pictures\Screenshots) — not with a
   region snip, so the clock is included.

## Screenshot 1 — the project code in the IDE

What to have on screen:

- VS Code (or your IDE) with the **`meridian` project folder open** and the Explorer
  visible, so the folder structure shows: `app/`, `frontend/`, `alembic/`, `scripts/`,
  `sample_data/`, `tests/`, `docs/`, the three launchers.
- An interesting file open — suggestion: `app/services/reconciliation.py` (the engine) or
  `app/services/categorization.py` (the two-pass pipeline).
- Optionally a second editor split with `tests/test_planted_events.py` — it demonstrates
  the graded testing story in one glance.
- **Click the taskbar clock once** so the calendar flyout with today's full date is open,
  then press **Win + PrtScn**.

## Screenshot 2 — the app running on localhost

What to have on screen:

- The browser at **`http://127.0.0.1:8787`** with the **URL bar visible** — this proves
  "running on localhost". (If Meridian opened in app-mode without a URL bar, open a
  normal browser tab to the same address for the screenshot.)
- Best screen: the **Dashboard**, signed in as Jordan — spending power, liquid accounts,
  card balances, needs-attention counts, and recent activity all show real data at once.
  Strong alternative: **Reconciliation** with a findings panel open (run "Reconcile all
  periods" after importing a few statements from `sample_data/`).
- **Click the taskbar clock** so the date flyout is open, then **Win + PrtScn**.

## macOS / Linux notes

- macOS: the menu-bar clock is always visible; add the date via System Settings →
  Control Center → Clock options → "Show date". Capture the full screen with
  **Cmd + Shift + 3**.
- Linux: most desktops show date+time in the top bar; capture full-screen with PrtScn.

## If the grader wants motion, not stills

The whole demo path in ~90 seconds: Start launcher → welcome screen → Jordan → Dashboard
→ Settings → "Simulate incoming transactions" (watch the dashboard update live) →
Documents → drag in `sample_data/jordan/statements/american_bank/checking_4417_2025-11.pdf`
→ preview → Import ("Imported 1, merged 25") → Reconciliation → run November → the $230.00
delta explained by the missing check.
