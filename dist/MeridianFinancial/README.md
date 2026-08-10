# Meridian Financial

An AI-powered personal finance platform that aggregates accounts across banks, credit
cards, payment apps, and crypto exchanges, reconciles live account data against monthly
statements, and answers plain-language questions about your actual spending — with the AI
model running **entirely on your own machine**. No transaction, balance, or merchant name
ever leaves it.

Built as Workshop 5.3 (Iteration 1), and built to be used: real persistence, real parsers,
real error handling, and a ledger-like interface designed for daily use.

## What it does

| Feature | In short |
|---|---|
| **Dashboard** | Spending power (liquid capital minus card balances due), cash flow, what needs attention |
| **Transaction review** | AI suggests a category with a confidence score; you confirm or override — every override teaches the rules |
| **Reconciliation** | Imported statements vs. the live feed; discrepancies surfaced in plain language, matched date-shifts never false-positive |
| **AI spending coach** | Chat grounded in real queries against your ledger; every answer shows the transactions it looked at |
| **Budgets & simulator** | Targets vs. actuals, and "what if I cut dining 30%?" projected from your real spending history |

## Quick start

**Prerequisite:** [Python 3.11+](https://www.python.org/downloads/). That's the only one.

**Get it:** download
[`dist/MeridianFinancial-v0.1.zip`](https://github.com/darrshen97-ui/Meridian/raw/main/dist/MeridianFinancial-v0.1.zip)
(the packaged release — smallest and cleanest), or download this repository as a ZIP;
both contain the prebuilt interface and run the same way. Extract it first — launchers do
not work from inside a compressed folder.

| Your computer | Do this |
|---|---|
| Windows | Double-click **`Start Meridian.bat`** |
| macOS | Double-click **`Start Meridian.command`** |
| Linux | Run **`./start.sh`** |

The launcher creates its own private Python environment on first run (a minute or two),
prepares the database, seeds two demo profiles, starts the server on `127.0.0.1:8787`
(falling back through 8799 if taken), and opens the app in a browser window. Keep the
console window open while you use the app — closing it quits Meridian.

### Demo profiles

| Profile | Email | Password |
|---|---|---|
| Jordan Reyes (primary demo, ~2,300 transactions) | `jordan@meridian.demo` | `rowhouse-ledger-26` |
| Priya Raman (isolation demo, ~1,100 transactions) | `priya@meridian.demo` | `lakefront-audit-26` |

Each profile's data is completely isolated — at the database, filesystem, and AI-tool
layers. You can also create your own profile from the welcome screen.

## Enabling AI features

Meridian's AI runs locally through [Ollama](https://ollama.com/download):

1. Install Ollama (one installer; it serves models on `127.0.0.1:11434`).
2. Pull the default model: `ollama pull qwen2.5:7b-instruct`
   (about 4.7 GB; runs on CPU, comfortably on any modest GPU).
3. Relaunch Meridian, or just use it — the app detects the model live.

Without Ollama, everything except the AI surfaces works normally: rule-based
categorization still runs, and the AI screens state plainly what's off and the one step
that turns it on. On slower machines, Settings offers `qwen2.5:3b-instruct` and a speed
test that recommends it when appropriate.

**Privacy stance:** the AI layer refuses to talk to any endpoint that doesn't resolve to
this machine. A cloud provider (Anthropic) exists behind the same interface for the course
architecture, but it is off by default and clearly labeled as sending data off-device.

## Loading the sample data

`sample_data/` ships with a year of generated statements for the demo profiles:

- **79 PDF statements** across American Bank, Chase (checking, Sapphire, auto loan), and
  Discover — three deliberately different layouts
- **26 CSV exports** — Venmo (monthly), Cash App (monthly), Binance and Gemini (annual)
- **12 OFX files** — Chase checking

Sign in as Jordan, open **Documents**, and drag any of them in. You'll see exactly what a
file contains before anything is imported; rows that already arrived via live sync merge
instead of duplicating. `sample_data/DATASET_GUIDE.md` lists the 13 planted events (a
duplicate charge, a never-cleared pending, a card compromise, …) so you can verify the app
catches every one.

## Environment variables

Everything has a working default; `.env.example` documents the full set. Copy it to
`.env` to change anything.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///data/meridian.db` | Point at PostgreSQL for deployment — schema is portable by design |
| `PORT` | `8787` | Preferred port; launcher falls back through `8799` |
| `DATA_DIR` | `data` | Database, uploaded documents, training captures |
| `JWT_SECRET` | auto-generated, persisted | Session signing; set explicitly for deployments |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Must resolve to loopback, enforced |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct` | Or choose in Settings |
| `LLM_PROVIDER` | `ollama` | `anthropic` only with an explicit key — sends data off-device |

## Project structure

```
MeridianFinancial/
├── Start Meridian.bat / .command / start.sh   ← double-click launchers
├── launcher.py               ← cross-platform launch logic (stdlib only)
├── app/                      ← FastAPI backend
│   ├── core/                 ← config, database, security, startup checks
│   ├── models/               ← SQLAlchemy tables (money = integer cents, UTC)
│   ├── repositories/         ← all SQL; every method scoped by user_id
│   ├── services/             ← auth, ingestion, sync, categorization,
│   │                            reconciliation, coach, simulation
│   ├── providers/            ← FinancialDataProvider (mock + Plaid stub),
│   │                            LLMProvider (Ollama + off-by-default Anthropic)
│   ├── parsers/              ← StatementParser registry (PDF / CSV / OFX)
│   ├── routers/              ← thin HTTP layer + SSE
│   └── static/               ← prebuilt React app (Node is never needed at runtime)
├── alembic/                  ← portable migrations (SQLite ⇄ PostgreSQL)
├── scripts/seed_demo.py      ← idempotent demo seeding
├── sample_data/              ← generated statements + DATASET_GUIDE.md
└── data/                     ← created on first run; delete it for a factory reset
```

Layering rule throughout: routers do no business logic, services do no SQL, repositories
do no HTTP.

## Troubleshooting

- **"Python was not found"** — install Python 3.11+ from python.org (on Windows, tick
  *Add python.exe to PATH*), then run the launcher again.
- **First launch is slow** — it's installing dependencies into its own `.venv` once.
  Subsequent launches take seconds.
- **The window opened as a plain browser tab** — app-mode needs Chrome or Edge; any
  browser works fine at the printed URL.
- **AI screens say the model is off** — start Ollama and pull the model (exact command is
  shown in the app with a copy button). Everything else keeps working meanwhile.
- **A statement fails to parse** — the Documents page says which file, which page, and
  why. Re-download the statement from your bank and upload again; partially-readable files
  import what they can and list what was skipped.
- **Port already in use** — the launcher tries 8787–8799 automatically; the console shows
  which one it chose.
- **Start over** — quit Meridian and delete the `data/` folder (profiles, documents, and
  the database live there; `sample_data/` is untouched). Delete `.venv/` to force a clean
  reinstall of dependencies.

## For developers

The repository (as opposed to the zip) also carries `frontend/` (React + Vite +
TypeScript; `npm run build` outputs into `app/static`), the deterministic dataset
generator (`scripts/generate_mock_data.py`), 154 pytest + 13 vitest tests
(`.venv/bin/python -m pytest`, `cd frontend && npm test`), and the build script
(`python scripts/build_zip.py` → `dist/MeridianFinancial-v0.1.zip`) and the deliverable
generator (`node scripts/build_deliverables.mjs` → `docs/deliverables/*.docx`). Project
documentation lives in `docs/` — the build plan (`BUILD_PLAN.md`), decision log
(`DECISIONS.md`, 23 entries), prompt and time logs, the development report
(`DEV_REPORT.md`), and the screenshot guide (`SCREENSHOT_GUIDE.md`).
