# Meridian Financial — Build Plan (Iteration 1)

**Status:** Draft — awaiting your approval before any code is scaffolded.
**Date:** 2026-08-09
**Source:** `docs/CLAUDE_CODE_BRIEF.md` (the authoritative spec). This plan restates scope,
answers the open questions in §20, records the decisions the brief left open, and defines the
milestone sequence with concrete checkpoints.

---

## 1. Scope restated

### In scope for Iteration 1

- Local multi-profile system: Argon2id passwords, JWT in an httpOnly SameSite=Strict cookie,
  absolute per-user data isolation (every repository method takes `user_id`), filesystem
  isolation under `data/{user_id}/`.
- Statement ingestion as a headline feature: PDF (`pdfplumber`), CSV, and OFX (`ofxparse`)
  upload → parse → normalize → **preview before write** → persist → dedupe → review queue.
  Parsers behind a `StatementParser` protocol, one class per format/institution, registered in
  a table.
- Seeded, deterministic mock dataset: two disjoint profiles, ~3,500 transactions across
  12 statement months (Aug 2025 – Jul 2026) plus an Aug 1–9, 2026 provider-only tail; ~79 PDFs,
  CSV exports in each platform's real column layout, 12 OFX files; all 13 planted events;
  `sample_data/DATASET_GUIDE.md` documenting each planted event with date and account.
- Live-sync architecture against `MockProvider` (cursor pagination, simulated latency, 5%
  transient failures, occasional 429s), sync runs recorded with cursor state, SSE pushing new
  transactions to the UI without refresh, "Sync now" control, "Simulate incoming transactions"
  dev tool.
- All five product features end to end: Dashboard, Transaction Review, Reconciliation,
  AI Spending Coach, Budget Simulator.
- Fully local AI via Ollama (`qwen2.5:7b-instruct` default) behind an `LLMProvider` protocol,
  with tool use, two-pass categorization (rules → LLM), the three-tier learning loop, coach
  grounding, reconciliation narration, and graceful degradation when Ollama is absent.
- Packaged zip with double-click launchers for Windows (primary), macOS, and Linux.

### Out of scope for Iteration 1

- Plaid integration (documented `PlaidProvider` stub only), real bank OAuth, cloud deployment,
  mobile/P2P sync, investment lot-level cost basis (schema accommodates it), LoRA fine-tuning
  job (training data capture only).

### Non-negotiables (checked at every milestone)

Profile isolation proven by test · statement upload genuinely works · zip launches by
double-click · degrades without the model, never breaks · financial data never leaves the
machine (loopback check at startup) · no fake functionality · money is never a float
(integer minor units end to end) · the UI meets the §13 design brief.

---

## 2. Answers to the open questions (§20)

### Q1 — Default local model

**Confirmed: `qwen2.5:7b-instruct`.** Evidence for the choice:

- Qwen2.5-Instruct models have first-class tool/function-calling support in Ollama's API and
  reliably emit schema-constrained JSON at the 7B size — the two capabilities this app leans on
  (categorization batches and coach tool use).
- Apache-2.0 licensed; ~4.7 GB at the default q4 quantization, so it fits comfortably in 8 GB
  RAM and runs acceptably on CPU for batch work.
- Alternatives considered: `llama3.1:8b` (good tool calling, heavier, more restrictive
  license), Mistral 7B (weaker structured output). Neither beats the default.

I can't measure your laptop from this environment, so the hardware recommendation is built as
a mechanism rather than a guess: on first AI use the app runs a latency self-test (one
representative categorization batch); if it exceeds ~20 s, Settings recommends
`qwen2.5:3b-instruct` with plain-language guidance. Model choice lives in Settings either way.

### Q2 — Matching across 1–3 day date shifts without false positives

Deterministic, layered matcher, run per account per statement period:

1. **Stage 0 — external ID.** If both rows carry the same `external_id`, match. Done.
2. **Stage 1 — exact hash.** `dedupe_hash` equality (account, posted date, amount, normalized
   description) → match.
3. **Stage 2 — shift-tolerant assignment.** Remaining rows are grouped by **exact
   `amount_minor`** (amounts must match to the cent — no tolerance here). Within a group, a
   statement/provider pair is a candidate only if |Δdate| ≤ 3 days **and** normalized
   description similarity ≥ 0.6 (token Jaccard) or same resolved merchant. Candidates are
   scored `|Δdays| + 2 × (1 − similarity)` and resolved by greedy lowest-score **one-to-one**
   assignment (ties: earlier date wins).
4. **Stage 3 — amount mismatch.** Still-unmatched rows with same merchant, |Δdate| ≤ 1, but
   different amounts → `amount_mismatch` finding with `delta_minor`.
5. **Leftovers.** Statement-only → `missing_in_provider`. Provider-only →
   `missing_in_statement`, except rows dated past the period end (+3-day grace) and pending
   rows, which surface as never-cleared-pending findings once the period closes.
6. **Duplicates** (within one source): same account, amount, and merchant within ≤ 3 days →
   `duplicate_suspected`.

False-positive guardrails, in order of importance: exact-amount grouping (a $15.99
subscription can never match a $22.99 one), the hard ±3-day window (consecutive monthly
charges are ~30 days apart, so recurring same-amount payments cannot cross-match), strict
one-to-one assignment (one statement row can never absorb two provider rows), and the
similarity floor. The planted-events test asserts the three seeded date-shift transactions
match silently and produce **zero** actionable findings.

Judgment call (recorded in DECISIONS.md): matched-but-shifted pairs are logged as
`date_shift` findings created **already resolved** — visible in the reconciliation detail for
transparency, never counted as discrepancies needing action. This uses the schema's
`date_shift` kind without violating the brief's "match them rather than flagging" instruction.

### Q3 — Bulk category application in the review queue

**Build it in Iteration 1** — and note that the brief already answered this itself: §14
screen 5 requires "bulk apply to matching merchants" while §20.3 asks whether to defer it.
Going with §14. Implementation: accepting a category in the review queue offers "Apply to N
matching transactions" using the same normalized merchant pattern that is written to
`user_corrections`, so one keystroke clears a merchant's whole backlog and teaches the rules
pass simultaneously.

### Q4 — Internal inconsistencies found

1. **§3 vs §12 (AI provider).** §3's in-scope list says "Claude API integration with tool
   use"; §5/§12 mandate a fully local Ollama default with `AnthropicProvider` disabled.
   Resolution per §12 and §18: the build ships LLM tool-use integration behind `LLMProvider`;
   Ollama is active, Anthropic is implemented but off by default and labeled as off-device.
   The DEV_REPORT writes this up as the deliberate architecture evolution the brief describes.
2. **§20.3 vs §14.5** — bulk apply, as above.
3. **PDF counts.** "6 accounts × 12 months ≈ 72" doesn't account for checking ••8123 closing
   in June 2026 (11 statements, not 12). Actual inventory: 71 bank/card PDFs + 8 auto-loan
   PDFs = **79**. `DATASET_GUIDE.md` will carry the exact per-account inventory.
4. **§6 "HTTPS-to-localhost".** The local app serves plain HTTP on `127.0.0.1` (a localhost
   zip has no certificate story). The JWT cookie is httpOnly + SameSite=Strict with the
   `Secure` flag off locally; the Cloud Run deployment path turns `Secure` on. Loopback-only
   binding is the actual security boundary locally.
5. **Non-negotiable #5 vs the optional `AnthropicProvider`.** As shipped, no AI code path can
   make an outbound call and the startup check verifies the active endpoint resolves to
   loopback. Enabling Anthropic requires an explicit Settings opt-in behind an unambiguous
   "sends data off-device" warning; only that explicit act relaxes the loopback check for the
   AI path. The default build satisfies #5 fully.
6. **Dataset "now".** The Aug 1–9, 2026 provider-only tail implies "today" ≈ Aug 9, 2026. To
   keep the generator deterministic, it pins its notion of now to **2026-08-09** rather than
   reading the wall clock. Recorded in DECISIONS.md.

---

## 3. Decisions the brief left open (mine to make, flagged for your veto)

| # | Decision | Reasoning |
|---|---|---|
| D-01 | **OFX files come from Chase checking ••7734** (12 monthly files) | Every bank in the dataset already has PDF statements, so OFX necessarily overlaps one of them. Overlapping Chase checking makes the overlap an asset: PDF + OFX + provider feed all describing the same rows is a live test that cross-format dedupe collapses to one row with all sources recorded. |
| D-02 | **System category taxonomy** (~20 top-level categories seeded as `is_system`, e.g. Income, Housing, Utilities, Groceries, Dining, Transport, Subscriptions, Insurance, Health, Travel, Transfers, Crypto, Fees…) | The brief requires categories but doesn't enumerate them. A fixed system set keeps LLM output validation strict; users add their own beneath it. |
| D-03 | **Reconciliation runs are explicit** ("Run reconciliation" per account/period, plus auto-run on statement import) | Keeps the engine deterministic and debuggable; avoids background magic the brief didn't ask for. |
| D-04 | **SSE over WebSockets** for live updates | One-directional server→client push is all the sync path needs; SSE is simpler, proxy-friendly, and reconnects for free. (Brief specifies SSE — recorded here because it also shapes the "Simulate incoming transactions" dev tool.) |
| D-05 | **Coach conversation history is session-scoped** (not persisted to DB in Iteration 1) | Keeps the small model's context tight; `ai_calls` still records every call. Persisting chat threads is an easy Iteration 2 add. |
| D-06 | **Port 8787, venv in `.venv` beside the launcher, data in `data/` beside the app** | Matches §15; everything the app writes stays inside its own folder so deleting the folder is a full uninstall. |

The SQLite-default / PostgreSQL-compatible schema tradeoff mandated in §5 is recorded in
`docs/DECISIONS.md` as required, since it must appear in the development report.

---

## 4. Architecture and repository layout

Layering rule enforced throughout: **routers do no business logic, services do no SQL,
repositories do no HTTP.** Services take and return domain objects, never ORM models.

```
meridian-financial/
├── Start Meridian.bat / Start Meridian.command / start.sh
├── README.md · .env.example · requirements.txt
├── app/
│   ├── main.py            # app factory, static serving, /health
│   ├── core/              # config (env), db session, security, startup loopback check
│   ├── models/            # SQLAlchemy ORM — the §7 tables, integer minor units, UTC
│   ├── domain/            # dataclasses/DTOs the services speak
│   ├── repositories/      # all SQL; every method takes user_id — no exceptions
│   ├── services/          # auth, ingestion, categorization, reconciliation, coach,
│   │                      #   simulation, sync
│   ├── providers/
│   │   ├── financial/     # FinancialDataProvider → MockProvider (active),
│   │   │                  #   PlaidProvider (documented stub)
│   │   └── llm/           # LLMProvider → OllamaProvider (active),
│   │                      #   AnthropicProvider (off by default)
│   ├── parsers/           # StatementParser protocol + registry; one class per layout
│   ├── routers/           # thin HTTP layer, SSE endpoint
│   └── static/            # prebuilt React bundle (build artifact, shipped in zip)
├── frontend/              # React 18 + Vite + TS + Tailwind; build-time only, never runtime
├── alembic/               # portable migrations (SQLite ∩ PostgreSQL only)
├── scripts/generate_mock_data.py   # seeded, deterministic; writes sample_data/
├── sample_data/           # generated statements, CSVs, OFX + DATASET_GUIDE.md
├── tests/                 # pytest: isolation, parser golden files, dedupe,
│                          #   reconciliation, all 13 planted events
└── docs/                  # this plan + the four living documents + brief
```

Stack as locked in §5: React 18 + Vite + TypeScript, Tailwind + CSS custom properties,
Recharts, FastAPI (async), SQLAlchemy 2 + Alembic, SQLite→Postgres via `DATABASE_URL`,
Ollama, pdfplumber, reportlab, ofxparse, Argon2id + JWT cookie, pytest + vitest. Fonts (Inter,
IBM Plex Mono) bundled locally so the app is correct offline.

---

## 5. Milestones

Order per §16. I stop and report at each checkpoint; the four living documents are updated as
part of every milestone, not afterward.

| # | Milestone | Definition of done (checkpoint) |
|---|---|---|
| 1 | Scaffold: folder structure, config from env, `.env.example`, health endpoint | `uvicorn` starts; `/health` returns 200; frontend dev shell builds |
| 2 | Data model + Alembic | All §7 tables migrate up **and down** cleanly on SQLite; schema contains nothing Postgres-incompatible |
| 3 | Auth + profiles + isolation | Create/login/switch flows work; pytest logs in as profile A and proves every list endpoint returns zero of profile B's rows; documents stored under `data/{user_id}/` |
| 4 | Mock data generator + documents | `sample_data/` fully populated from a fixed seed; regeneration is byte-identical; all 13 planted events present; `DATASET_GUIDE.md` written |
| 5 | Statement parsers + ingestion pipeline | All ~91 sample documents (79 PDF, 12 OFX, CSVs) parse via golden-file tests; preview-before-import works; failures are specific and recoverable |
| 6 | Provider layer + MockProvider + sync + SSE | Incremental cursor sync with retry/backoff against injected failures; new transactions appear in the browser without refresh |
| 7 | Design system + shell + navigation | §13 tokens implemented; ledger-rule table primitive built; all five view states scaffolded; keyboard nav + focus rings |
| 8 | Dashboard, Accounts, Transactions, Documents | Real data rendering end to end, no placeholders; spending power computed from `is_liquid` only |
| 9 | Local model + categorization + learning loop | Rules pass → LLM pass → review queue; <0.80 confidence never auto-applies; corrections write `user_corrections` + JSONL training capture; ambiguous merchants land in review |
| 10 | Reconciliation engine + narration | All 13 planted events detected by test; date shifts match silently; narration is model-generated from structured findings only |
| 11 | Coach + tool use | Answers grounded in real queries; shows which transactions informed each answer; tool loop capped at 4 calls; honest when data is insufficient |
| 12 | Budgets + simulator | Projection math deterministic in Python from real historical distribution; model explains, never computes |
| 13 | Hardening: error handling, validation, responsive (1280→375), a11y | Five states verified on every view; `prefers-reduced-motion`; no "Oops" anywhere |
| 14 | Packaging + launcher + zip | Clean-machine test: fresh extract, double-click, browser opens, app works — with and without Ollama installed; result documented |
| 15 | Assignment deliverables | §18 complete: PROMPT_LOG, DEV_REPORT, TIME_LOG, DECISIONS, SCREENSHOT_GUIDE, README |

Design checkpoint per §21: before milestone 7 I'll present the design plan (layout structure,
the ledger-rule system, type specimens) and screenshot/critique the UI against §13 as views
land in milestones 7–8.

---

## 6. Testing

- **Isolation:** the profile-A/profile-B zero-leakage pytest (non-negotiable #1), plus a
  repository-layer audit test asserting every repository method signature requires `user_id`.
- **Parsers:** golden-file tests for every generated sample document; page-break, layout, and
  date-format variants covered by construction.
- **Dedupe & reconciliation:** unit tests on the hash, the assignment matcher (including
  recurring same-amount charges straddling the window), and an integration test asserting all
  13 planted events are detected with zero false positives on the date-shift trio.
- **AI layer:** provider protocol tested against a fake LLM; schema-validation rejects
  malformed/hallucinated categories into the review queue; loopback startup check tested.
- **Frontend:** vitest smoke-render of every route plus logic tests for money formatting
  (integer minor units in, formatted string out) and spending-power composition.
- **Clean-machine test** for the zip, documented in the README and DEV_REPORT.

---

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| 7B model too slow/weak on your laptop | Latency self-test + 3B fallback path; small rigid prompts; batches of 10–20; review queue absorbs low confidence by design |
| PDF parsing brittleness | We control the generator, but layouts deliberately vary; golden tests per document; partial-parse recovery with specific errors |
| Windows launcher edge cases (paths with spaces, missing Python, antivirus slowness) | Launcher written defensively, clear messages instead of stack traces; clean-machine test on the real zip |
| Recurring same-amount transactions confusing the matcher | Exact-amount grouping + ±3-day cap + one-to-one assignment; explicit regression test |
| Scope pressure from 15 milestones | Strict milestone order, checkpoint reports, PyInstaller stretch goal explicitly deferred until everything else is done |

---

## 8. Living documents

Maintained continuously from milestone 1: `PROMPT_LOG.md` (every prompt, timestamped, outcome
noted), `TIME_LOG.md` (per milestone), `DECISIONS.md` (every judgment call with reasoning),
`DEV_REPORT.md` (drafted progressively, including the local-model architecture evolution
story). `SCREENSHOT_GUIDE.md` lands with milestone 15.

---

## 9. What I need from you

1. **Approve this plan** (or mark up what to change) — per the brief, I don't scaffold until
   you've seen it.
2. ~~Create the separate GitHub repository.~~ **Done** — `darrshen97-ui/meridian` was created
   manually and this project now lives there (see D-000 in `docs/DECISIONS.md`).
3. Optional veto on decisions D-01…D-06 above.
