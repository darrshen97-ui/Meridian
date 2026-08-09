# Meridian Financial — Build Brief for Claude Code

**Read this entire file before writing any code.** This is the authoritative specification for
Iteration 1. Where this document conflicts with your defaults, this document wins.

---

## 0. How to use this document

1. Read the whole brief.
2. Produce a written build plan (`docs/BUILD_PLAN.md`) that restates scope, milestones, and any
   decisions you're making that this brief left open. Show it to me before you scaffold.
3. Build in the milestone order given in §16. Stop at each milestone checkpoint and report.
4. Maintain the four living documents in §18 as you go — do not leave them until the end.
5. When you hit an ambiguity, make the smallest reasonable decision, note it in
   `docs/DECISIONS.md`, and keep moving. Do not stall waiting for me.

---

## 1. Context

I'm building this app for two audiences at once, and both matter:

**Audience A — the coursework.** This is the Workshop 5.3 assignment for an AI/full-stack web
development course. It's graded against a rubric and has specific deliverables (§18). The app must
run locally and be demonstrably functional in a browser on localhost.

**Audience B — me.** This is the important one. I am not building a throwaway assignment app. I
intend to actually use this to manage my own money after the course ends. Every decision should be
made as if this is going into real daily use: real error handling, real data integrity, a UI I
want to open. Do not build a demo-grade shell with stubbed interiors.

**Prior app (App #1) was GridPilot** — a frontend-only prototype in the energy/utility space,
deployed as a static site to Firebase Hosting. It had no backend, no database, and no real model
calls; retrieval was simulated with keyword scoring over a static document set. The lessons from
that build are in §19 and they shape a lot of this brief.

---

## 2. What Meridian Financial is

An AI-powered personal finance platform that aggregates accounts across banks, credit cards,
payment apps, and crypto exchanges, reconciles live account data against monthly statements, and
provides an AI spending coach that answers plain-language questions about actual spending.

The core insight the product is built around: **existing finance apps are good at aggregation and
bad at interpretation.** They show you numbers. They don't tell you what the numbers mean, whether
you can afford the thing you're about to buy, or that your streaming subscription quietly went up
$7 in January. Meridian's job is interpretation.

Five features carry the product:

| Feature | What it does |
|---|---|
| **Dashboard** | Balances, spending power (liquid capital only), cash flow, what needs attention |
| **Transaction Review** | Human-in-the-loop queue; AI suggests category + confidence, I confirm or override |
| **Reconciliation** | Live account data vs. uploaded statements; surfaces discrepancies in plain language |
| **AI Spending Coach** | Chat interface; answers questions by querying my real transaction data via tool use |
| **Budget Simulator** | "What if I cut dining by 30%?" — projects against actual historical spending |

**Spending power** is a specific term with a specific definition: liquid capital only. Checking +
savings + payment-app balances, minus known upcoming obligations. It explicitly **excludes**
investments and crypto. Don't blur this.

---

## 3. Iteration 1 scope

### In scope

- Local multi-profile system with real credential handling and strict per-user data isolation
- **Statement ingestion as a first-class, fully working feature** — PDF, CSV, and OFX upload,
  parse, normalize, persist, and surface in the UI
- A complete generated mock dataset covering one year across every platform the app supports (§9)
- Live-sync architecture built and working against a mock provider (§11)
- All five features above, functional end to end
- Claude API integration with tool use for categorization, reconciliation narration, coaching, and
  simulation
- Packaged zip with a double-click launcher that opens the app in a browser window (§15)

### Out of scope for Iteration 1

- **Plaid.** Do not build the Plaid integration. Build the provider interface it will slot into
  (§11) and leave a documented `PlaidProvider` stub. This is deliberate — I want the ingestion
  and sync architecture proven against mock data before I put real credentials anywhere near it.
- Real bank OAuth flows
- Cloud deployment (the architecture targets Google Cloud Run; Iteration 1 runs local only)
- Mobile app / peer-to-peer device sync
- Investment lot-level cost basis tracking (schema should accommodate it; UI can wait)

---

## 4. Non-negotiables

These are the things I will check first. If any of these fail, the build isn't done.

1. **Profile isolation is absolute.** Every query is scoped by `user_id`. There is no code path
   that returns another profile's data. Write a test that proves it.
2. **Statement upload actually works.** I drop in a PDF from the sample set, it parses, and the
   transactions appear correctly attributed with correct dates and amounts. Not a stub.
3. **The app launches from a zip by double-clicking one file.** No terminal commands, no manual
   `npm install`, no reading a setup guide. It opens a browser window and works.
4. **It runs without the local model installed** — degraded but not broken. If Ollama or the
   model is absent, AI features show a clear, non-apologetic empty state explaining what's
   unavailable and the one step to enable it. Deterministic rules-based categorization still runs.
5. **Financial data never leaves the machine.** The AI layer talks only to a localhost model
   endpoint. There are no outbound network calls anywhere in the AI code path, and a startup
   check verifies the model endpoint is bound to 127.0.0.1.
6. **No fake functionality.** If something isn't implemented, the UI says so plainly. Do not wire
   a button to a `console.log` or a hardcoded response. This was the single biggest weakness of
   App #1 and I'm not repeating it.
7. **Money is never a float.** Store minor units as integers (cents) or use `Decimal` end to end.
8. **The UI is genuinely good.** See §13. This is not a checkbox.

---

## 5. Technology stack

Locked. These match the architecture I submitted for Part 2 of the workshop, so don't substitute.

| Layer | Choice | Notes |
|---|---|---|
| Frontend | React 18 + Vite + TypeScript | Built to static assets, served by the backend |
| Styling | Tailwind CSS + CSS custom properties for tokens | Tokens in §13 are the source of truth |
| Charts | Recharts | Only where a chart earns its place |
| Backend | Python 3.11+ / FastAPI | Async throughout; this is the justification I wrote |
| ORM | SQLAlchemy 2.x + Alembic | |
| Database | **SQLite locally, PostgreSQL-compatible schema** | See the note below |
| AI | **Local LLM via Ollama** (localhost only) | Default `qwen2.5:7b-instruct`; see §12 |
| AI abstraction | `LLMProvider` protocol | `OllamaProvider` active; `AnthropicProvider` optional, off by default |
| PDF parsing | `pdfplumber` | |
| PDF generation (mock data) | `reportlab` | |
| OFX parsing | `ofxparse` | |
| Auth | Argon2id password hashing, JWT in httpOnly cookie | |
| Testing | `pytest` + `vitest` | |

### Database note — read this carefully

My submitted architecture specifies PostgreSQL on Cloud SQL, and that remains the target for
deployment. But requiring a Postgres install would break non-negotiable #3 — the whole point of
the zip is that it just runs.

So: **use SQLAlchemy with a `DATABASE_URL` environment variable, defaulting to SQLite.** Constrain
the schema to the intersection of SQLite and PostgreSQL — no SQLite-specific types, no Postgres-only
features in Iteration 1, all migrations via Alembic and portable. Moving to Cloud SQL must be a
config change, not a rewrite. Document this explicitly in `docs/DECISIONS.md`, because it's a
tradeoff I need to be able to explain in the development report.

---

## 6. Architecture

```
Browser (React SPA, served as static assets from FastAPI)
  │  REST + JSON over HTTPS-to-localhost, JWT cookie
  ▼
FastAPI Router  ──────────────────────────────────────────────┐
  ├── Auth Service          profiles, Argon2id, sessions      │
  ├── Ingestion Service     statement upload + provider sync  │
  ├── Categorization        rules pass → LLM pass → review    │
  ├── Reconciliation        statement ledger vs. live ledger  │
  ├── Coach Service         tool-use orchestration            │
  └── Simulation Service    budget projections                │
  │                                                            │
  ├──▶ Local LLM (Ollama @ 127.0.0.1, tool use)               │
  │        └──▶ tools execute against DB, user-scoped ────────┤
  ├──▶ Provider layer  ──▶ MockProvider (active)              │
  │                     └─ PlaidProvider (stub, Iteration 2)  │
  └──▶ SQLAlchemy ──▶ SQLite (local) / PostgreSQL (deployed) ─┘

No AI code path makes an outbound network call. Financial data stays on this machine.
```

Layering rule: **routers do no business logic, services do no SQL, repositories do no HTTP.**
Services take and return domain objects, not ORM models. This is the discipline App #1 lacked and
it's why App #1 became hard to change.

---

## 7. Data model

Tables. All money columns are integer minor units. All timestamps UTC.

- **users** — `id`, `display_name`, `email`, `password_hash`, `created_at`, `last_login_at`
- **institutions** — `id`, `user_id`, `name`, `kind` (bank | credit | payment_app | exchange | loan),
  `provider_key`, `status` (active | closed), `closed_at`, `closed_reason`
- **accounts** — `id`, `user_id`, `institution_id`, `display_name`, `mask` (last 4), `type`
  (checking | savings | credit_card | loan | crypto | payment_app), `currency`,
  `is_liquid` (bool — drives spending power), `opened_at`, `closed_at`
- **balances** — `id`, `account_id`, `as_of`, `current_minor`, `available_minor`, `source`
- **transactions** — `id`, `user_id`, `account_id`, `posted_date`, `transaction_date`,
  `description_raw`, `description_clean`, `merchant`, `amount_minor` (signed), `currency`,
  `type` (debit | credit | transfer), `pending` (bool), `source` (statement | provider | manual),
  `source_document_id`, `external_id`, `category_id`, `category_confidence`,
  `category_source` (rules | llm | user), `reviewed_at`, `dedupe_hash`
- **categories** — `id`, `user_id` (nullable for system defaults), `name`, `parent_id`, `is_system`
- **user_corrections** — `id`, `user_id`, `merchant_pattern`, `category_id`, `created_at` —
  feeds back into future categorization
- **documents** — `id`, `user_id`, `account_id`, `kind` (pdf_statement | csv_export | ofx),
  `filename`, `stored_path`, `period_start`, `period_end`, `sha256`, `parse_status`,
  `parse_error`, `uploaded_at`
- **budgets** — `id`, `user_id`, `category_id`, `period_type`, `period_start`, `target_minor`
- **reconciliations** — `id`, `user_id`, `account_id`, `period_start`, `period_end`,
  `statement_ending_minor`, `computed_ending_minor`, `status`, `run_at`
- **reconciliation_findings** — `id`, `reconciliation_id`, `kind` (missing_in_provider |
  missing_in_statement | amount_mismatch | duplicate_suspected | date_shift),
  `transaction_id`, `counterpart_id`, `delta_minor`, `narrative`, `resolved_at`
- **sync_runs** — `id`, `user_id`, `provider_key`, `started_at`, `finished_at`, `status`,
  `cursor`, `records_ingested`, `error`
- **audit_log** — `id`, `user_id`, `event`, `detail_json`, `created_at` — append-only; log every
  login, upload, sync, AI call, category override, and settings change
- **ai_calls** — `id`, `user_id`, `feature`, `model`, `input_tokens`, `output_tokens`,
  `latency_ms`, `status`, `created_at` — I want visible cost accounting

**Dedupe:** `dedupe_hash = sha256(account_id | posted_date | amount_minor | normalized_description)`.
When statement and provider data describe the same transaction, they collapse to one row with both
sources recorded. Getting this right is the heart of reconciliation — do not shortcut it.

---

## 8. Profiles and data isolation

On first launch, no profiles exist. The app shows a create-profile screen.

- Create profile: display name, email, password (Argon2id, minimum 10 chars, zxcvbn-style strength
  meter)
- Login: email + password → JWT in an httpOnly, SameSite=Strict cookie
- Profile switcher in the UI header; switching requires re-authentication
- Two seeded demo profiles ship with the app (§9), each with its own complete, disjoint dataset
- **Every repository method takes `user_id` and filters on it.** No exceptions, including admin or
  debug endpoints. Add a pytest that logs in as profile A and asserts that every list endpoint
  returns zero rows belonging to profile B.
- Uploaded documents are stored under `data/{user_id}/documents/` — isolation at the filesystem
  level too

---

## 9. Mock dataset — detailed specification

This is the part that proves the app works, so build it properly. Write a **seeded, deterministic
generator** (`scripts/generate_mock_data.py`, fixed random seed) that regenerates the identical
dataset every time. Generated artifacts go in `sample_data/` and ship inside the zip.

### Period

**August 1, 2025 → July 31, 2026** = 12 complete statement months.

Plus: **August 1–9, 2026 exists only in the live-sync provider feed, not in any statement.** This
is intentional and important. Statements lag reality by design, and this gap is what makes the
reconciliation feature demonstrable rather than theoretical.

### Profile 1 — "Jordan Reyes" (primary demo)

Mirrors the full breadth of institutions the app is designed to connect to. ~2,400 transactions.

| Institution | Accounts |
|---|---|
| American Bank | Checking ••4417, Checking ••8123 (closed June 2026), Savings ••2290 |
| Chase | Checking ••7734, Sapphire credit card ••1902, Auto loan ••5561 (paid off March 2026) |
| Discover | It Card credit ••6088 |
| Venmo | Balance account |
| Cash App | Balance account |
| Binance | BTC, ETH holdings |
| Gemini | BTC, SOL holdings |

Baseline financial shape: biweekly salary deposit, rent, utilities, groceries, dining, transit,
subscriptions, insurance, occasional transfers between own accounts, weekly small crypto DCA buys.

### Planted events — the dataset must contain all of these

These exist so that every feature has something real to find. Document each one in
`sample_data/DATASET_GUIDE.md` with the date and the account, so I can verify the app catches it.

1. **Duplicate charge** — same merchant, same amount, 2 days apart (Feb 2026, Chase Sapphire)
2. **Missing in provider** — a transaction present on the statement but absent from the API feed
   (Nov 2025, American Bank checking)
3. **Never-cleared pending** — present in the provider feed, absent from the statement
   (Mar 2026, Discover)
4. **Subscription price increase** — a streaming service goes $15.99 → $22.99 (Jan 2026)
5. **Card compromise** — three out-of-pattern foreign charges over 36 hours (June 2026), account
   ••8123 closed, replacement transactions resume on ••4417
6. **Ambiguous merchant strings** — at least 40 transactions with descriptors like
   `SQ *BLUE STEM`, `TST* MERIDIAN 04`, `PAYPAL *STGHRSE`, `POS DEBIT 8871 WDM IA` — these should
   land in the review queue with low confidence, not be silently guessed
7. **Seasonal spike** — December 2025 discretionary spending ≈ 2.1× the monthly baseline
8. **One-time large expense** — $1,840 transmission repair (Oct 2025)
9. **Vacation cluster** — one week of concentrated travel spending in a different state (Mar 2026)
10. **Income change** — biweekly net rises $3,180 → $3,510 (Apr 2026)
11. **Auto loan payoff** — the recurring $412 payment stops after March 2026
12. **Crypto activity** — weekly DCA buys throughout, one large partial sale (May 2026)
13. **Date shift** — three transactions where the statement posted date and provider date differ
    by 1–3 days, to test that reconciliation matches them rather than flagging false positives

### Profile 2 — "Priya Raman" (isolation proof)

Deliberately disjoint: different institutions (Ally, Capital One, Fidelity, Coinbase, PayPal),
different city, different income level and spending shape, ~1,100 transactions, 12 months. Shares
zero merchants with Profile 1 where avoidable. Its only job is to make cross-profile leakage
immediately visible if it ever happens.

### Documents to generate

Realistic enough that the parsers are doing genuine work, not reading a convenient format.

- **PDF monthly statements** (`reportlab`) — American Bank ×3 accounts, Chase checking, Chase
  Sapphire, Discover = 6 accounts × 12 months ≈ **72 PDFs**. Each with: institution letterhead,
  masked account number, statement period, beginning and ending balance, a ruled transaction table
  with date / description / amount / running balance, and a summary block. Vary the layout between
  institutions — different column orders, different date formats (`01/15/26` vs `Jan 15, 2026`),
  one with transactions split across a page break. The parser should have to be robust.
- **Chase auto loan statements** — 8 PDFs, through payoff
- **CSV exports** — Venmo, Cash App, Binance, Gemini. Use each platform's real-world export column
  layout and quirks (Venmo's multi-row header, Binance's UTC timestamps, Gemini's separate fee
  column). 4 platforms × 12 monthly files, or annual files where that platform exports annually.
- **OFX/QFX** — one bank, 12 files, to prove multi-format ingestion

### Provider feed fixtures

The mock sync provider (§11) serves the same underlying ledger through a simulated API — including
the deliberate divergences from the statements listed above, plus the Aug 1–9, 2026 tail that no
statement covers.

---

## 10. Statement ingestion

This is a headline feature for Iteration 1, not a utility. Build it accordingly.

**Flow:** drag-and-drop or file picker → SHA-256 dedupe check (reject exact re-upload with a clear
message) → detect format → route to parser → normalize to a common transaction shape → present a
**preview screen showing exactly what will be imported before anything is written** → user confirms
→ persist with `source = statement` and a `source_document_id` → run dedupe against existing
provider rows → queue uncategorized transactions for review.

**Requirements:**

- Multi-file upload; each file gets independent status
- Real progress indication for multi-page PDFs
- Parse failures are recoverable and specific: which file, which page, what went wrong, what I can
  do about it. Never a generic "upload failed."
- A partially-parsed statement imports what it could and tells me exactly what it skipped
- Account matching: infer the target account from the masked number in the document; if ambiguous,
  ask me rather than guessing
- Every uploaded document is retained and browsable in a **Documents** view, with the ability to
  see which transactions came from which document
- Parsers live behind a `StatementParser` protocol with one implementation per format/institution,
  registered in a table. Adding a new bank's layout should mean writing one class.

---

## 11. Live sync architecture

Plaid is deferred, but the sync machinery is not. Build it now against a mock so that Iteration 2
is a provider swap.

```python
class FinancialDataProvider(Protocol):
    async def list_accounts(self, user_id: str) -> list[AccountDTO]: ...
    async def fetch_transactions(
        self, user_id: str, account_id: str, cursor: str | None
    ) -> TransactionPage: ...
    async def fetch_balances(self, user_id: str, account_id: str) -> BalanceDTO: ...
```

- **`MockProvider`** — active. Serves the generated ledger with realistic behavior: cursor-based
  pagination, 200–900ms simulated latency, a configurable 5% transient failure rate, and occasional
  429s. Your retry, backoff, and error-surfacing code must actually be exercised.
- **`PlaidProvider`** — stub class, documented, raises `NotImplementedError`, with a comment noting
  exactly which methods map to which Plaid endpoints.
- **Sync runs** are recorded in `sync_runs` with cursor state so incremental sync is real
- **Push updates to the UI** over Server-Sent Events. When a sync brings in new transactions, the
  dashboard updates without a refresh. This must visibly work.
- **A dev control** in Settings: "Simulate incoming transactions" — injects 1–5 new plausible
  transactions into the mock provider so I can watch the live path work on demand. Label it clearly
  as a development tool.
- A manual "Sync now" control with honest state: last sync time, in-progress indicator, per-account
  result, and a clear error if it failed.

---

## 12. AI integration — fully local

**Hard requirement: the model runs in-house.** This app processes my real financial data, and no
transaction, balance, merchant name, or derived summary may ever leave the machine. The AI layer
talks exclusively to a model served on localhost.

### Runtime

- **Ollama** as the model server, bound to `127.0.0.1:11434`. It's the pragmatic choice: one
  installer on Windows, a model registry, an OpenAI-compatible local API, structured JSON output,
  and function calling on supported models.
- **Default model: `qwen2.5:7b-instruct`** — strong function calling and structured output for its
  size, Apache-licensed, runs acceptably on CPU and well on any modest GPU.
- **Hardware fallback: `qwen2.5:3b-instruct`.** On first AI use, run a quick latency self-test and
  recommend the smaller model if the 7B is too slow on this machine. Put the model choice in
  Settings with plain-language guidance.
- All AI calls go through an **`LLMProvider` protocol**. `OllamaProvider` is the active
  implementation. Keep an `AnthropicProvider` implementation behind the same interface, **disabled
  by default**, clearly labeled in Settings as sending data off-device if ever enabled. It exists
  because my submitted course architecture references the Claude API and because the abstraction
  costs nothing; the product default is local, full stop.
- **Isolation checks:** on startup, verify the configured model endpoint resolves to a loopback
  address and refuse to run AI features otherwise. Log every AI call to `ai_calls` (keep the
  table; cost is zero but latency and token counts still matter for tuning).

### Categorization — two-pass

1. **Rules pass first.** Deterministic merchant-pattern matching, plus every prior
   `user_corrections` entry for this user. Most transactions never reach the model. My past
   corrections always beat a fresh model guess.
2. **LLM pass** for what's left. Batch 10–20 transactions per call (smaller batches than a
   frontier model would get — a 7B needs tighter, simpler prompts). Constrain output with
   Ollama's JSON-schema structured output: category, confidence 0–1, brief reason. Validate
   against the category list; anything malformed or hallucinated goes to the review queue, never
   into the ledger.
3. **Confidence < 0.80 → review queue.** Never auto-apply a low-confidence category. Calibrate
   expectations: a local 7B will send more to review than a frontier model would. That's fine —
   the review queue is a feature, and it's the engine of the learning loop below.
4. **Every override writes a `user_corrections` row** and applies to future matching merchants.

### The learning loop — how the model learns from me

Three tiers, honest about what each one is:

- **Tier 1 — deterministic memory (instant).** Every correction becomes a merchant-pattern rule.
  The next matching transaction never reaches the model at all. This is the strongest form of
  learning in the system and it works from the first correction.
- **Tier 2 — few-shot personalization (per call).** When the model is asked to categorize, retrieve
  the most relevant of my past corrections — match on normalized merchant tokens first, embedding
  similarity if cheap to add — and inject them into the prompt as worked examples ("this user
  files SQ *BLUE STEM under Dining"). The model's behavior adapts to my taxonomy and habits on
  every call without touching weights. Store retrieval hit-rate so we can see it working.
- **Tier 3 — fine-tuning path (designed now, run later).** Maintain an exportable training set:
  every correction saved as an instruction/response pair in JSONL
  (`data/{user_id}/training/corrections.jsonl`). Iteration 2 can run a periodic LoRA fine-tune
  from it. **Do not build the training job in Iteration 1** — just ensure the data capture is
  clean, documented in `docs/DECISIONS.md`, and genuinely sufficient to train from later.

The Coach also benefits from tier 2: retrieve my correction history and category taxonomy into its
context so its language matches how I actually file things.

### Prompt discipline for a small model

A 7B is not a frontier model; design for it rather than pretending otherwise. Short, rigid system
prompts. One job per call. Structured output schemas everywhere. No long multi-step agentic
chains — tool use loops cap at 4 calls per question, and if the model can't resolve within that,
it says what it found and what it couldn't determine. Test every prompt against the actual model
during development, not against intuition.

### Tools exposed to the model

Same tool surface regardless of provider. Scoped to the authenticated user at the tool-execution
layer — the model never receives a `user_id` parameter it could manipulate, and tool results are
truncated to sane sizes before entering the small model's context.

- `query_transactions(date_range, merchant?, category?, min_amount?, max_amount?, limit)`
- `get_account_balances(include_non_liquid: bool)`
- `get_budget_targets(period)`
- `fetch_category_history(merchant)`
- `get_spending_summary(group_by, period)`

### Coach behavior

Conversational, grounded, and honest. It must query before answering — no vibes-based financial
advice. When the data doesn't support an answer, it says so. It surfaces which transactions it
looked at so I can verify the reasoning. It should be capable of saying "you can't comfortably
afford this" without hedging it into uselessness.

### Reconciliation narration

The engine does deterministic matching and produces structured findings. The model's only job is
turning a finding into one clear sentence. Never let the model do the matching — that's arithmetic
and it belongs in Python.

### Budget simulation

Deterministic projection math in Python, using the user's real historical spending distribution.
The model explains the result and flags second-order effects. Same principle: math in code,
language in the model.

### Degradation without the model

If Ollama isn't installed or the model isn't pulled: rules-based categorization runs, everything
not AI-dependent works normally, and AI surfaces show a direct empty state naming the one step to
enable it ("Install Ollama and run `ollama pull qwen2.5:7b-instruct`", with a copy button). No
apologetic tone, no broken-looking UI. Settings shows live model status: installed, loaded,
last-call latency.

---

## 13. Design system

I care about this a great deal. The UI is the product. Read this section twice.

### Direction

**Apple's design sensibility applied to a financial ledger.** Constraint over decoration.
Intentionality in every choice. One accent color, used sparingly and only where it means something.
Flat, structured layout — **not a grid of rounded cards with drop shadows**. An 8-point spacing
grid. Tabular figures everywhere numbers appear. Motion only in response to a user action, never
ambient.

### What to avoid

Do not produce the current default AI-generated look. Specifically avoid: cream `#F4F1EA`
backgrounds with terracotta accents; near-black backgrounds with one acid-green accent; a wall of
uniform rounded cards each containing one big number and a percentage delta; gradient hero blocks;
purple-to-blue gradients on anything. If a choice feels like the thing you'd produce for any
dashboard brief, it's wrong for this one.

### The signature

**The ledger rule.** A financial statement is a printed artifact — ruled lines, right-aligned
columns, monospaced figures that align digit-for-digit. That vernacular is the app's structural
identity. Hairline rules separate rows rather than card borders separating boxes. Numbers align on
the decimal. The interface should feel like a well-set ledger that happens to be intelligent, not
like a SaaS dashboard that happens to hold financial data.

Spend the boldness here and keep everything else quiet.

### Tokens

```css
/* Light */
--canvas:        #FBFBFA;   /* warm-neutral near-white, not cream */
--surface:       #FFFFFF;
--ink:           #16181D;   /* primary text */
--ink-muted:     #6E7178;   /* secondary text */
--ink-faint:     #9A9CA1;   /* tertiary, timestamps, units */
--rule:          #E6E6E4;   /* hairline — the primary structural device */
--rule-strong:   #C9C9C6;
--accent:        #14594A;   /* deep pine — the ONLY accent */
--accent-wash:   #E8F0ED;
--positive:      #14594A;   /* money in — same as accent, deliberately */
--negative:      #1F2126;   /* money out — ink, not red */
--attention:     #A9542A;   /* needs review — reserved, used rarely */
--critical:      #8C2F26;   /* genuine problems only */

/* Dark */
--canvas:        #0E0F11;
--surface:       #16181B;
--ink:           #EDEDEA;
--ink-muted:     #9B9EA3;
--rule:          #26282C;
--accent:        #5FA891;
```

**Color discipline:** ordinary spending is not red. Red is for problems, not for the normal
outflow of living. Reserve `--attention` for the review queue and `--critical` for reconciliation
failures and genuine errors. If more than ~5% of a screen is colored, cut back.

### Typography

- **UI / body:** Inter (variable). Sentence case throughout.
- **Ledger figures, statement views, account numbers, all tabular data:** IBM Plex Mono.
  Every numeric column uses `font-variant-numeric: tabular-nums`.
- **Headings:** Inter at deliberate weights and sizes. No decorative display face — restraint is
  the point.
- Scale: 12 / 13 / 15 / 17 / 20 / 24 / 32. Weights: 400 / 500 / 600 only.
- Ship the fonts locally in the bundle. The app must look correct offline.

### Layout

- 8-point spacing grid, no exceptions
- Persistent left navigation, content area with generous margins
- Data tables are the primary layout primitive, not cards
- Maximum content width ~1240px; the app is comfortable at 1280 and works down to 375
- Full keyboard navigation with visible focus rings; `prefers-reduced-motion` respected

### Motion

Only in response to user action. Number transitions on data change (150ms). Row expansion (200ms
ease-out). Page transitions: none. No skeleton shimmer — use a quiet, honest loading state instead.

### Required states

Every view implements all five: **loading, empty, partial, error, populated.** Empty states are
invitations to act, not apologies. Errors state what happened and what to do — in the interface's
voice, not a person's. No "Oops!" Ever.

### Copy

Active voice. A control names exactly what happens when it's used. An action keeps the same name
through the whole flow — the button that says "Import" produces a toast that says "Imported."
Name things by what I control, not by how the system is built.

---

## 14. Screens

1. **Welcome / Profile select** — create or choose a profile. First-run creates one.
2. **Dashboard** — spending power prominently and unambiguously; account balances; this month vs.
   last; what needs attention (review queue count, unresolved reconciliation findings); recent
   activity. This screen answers "am I okay?" in under three seconds.
3. **Accounts** — all institutions and accounts, balances, last sync, connection status. Closed
   accounts visible but visually de-emphasized.
4. **Transactions** — the ledger. Filter, search, sort, date range. Inline category editing.
   Source indicator (statement / provider / both). This is where I'll spend the most time; make it
   fast and keyboard-friendly.
5. **Review queue** — only low-confidence and unreviewed transactions. Optimized for speed:
   keyboard shortcuts, one-key accept, bulk apply to matching merchants. I should be able to clear
   40 transactions in two minutes.
6. **Reconciliation** — per account per period. Statement ending balance vs. computed. Findings
   listed with plain-language narration and a resolve action.
7. **Documents** — every uploaded statement, its parse status, period, and the transactions it
   produced. Upload entry point.
8. **Coach** — chat. Shows which transactions informed each answer.
9. **Budgets & Simulator** — targets by category, actual vs. target, and the what-if tool.
10. **Settings** — profile, API key status, sync controls, AI cost accounting (from `ai_calls`),
    audit log viewer, dev tools.

---

## 15. Packaging and launch

**Deliverable:** `dist/MeridianFinancial-v0.1.zip`

**Requirement:** I double-click one file and the app opens in a browser window, working.

### Contents

```
MeridianFinancial/
  Start Meridian.bat        ← Windows (primary target — I'm on a Windows laptop)
  Start Meridian.command    ← macOS
  start.sh                  ← Linux
  README.md
  .env.example
  app/                      ← FastAPI backend
  app/static/               ← prebuilt React assets (no Node needed at runtime)
  sample_data/              ← generated statements, CSVs, OFX + DATASET_GUIDE.md
  data/                     ← created on first run
```

### Launcher behavior

1. Detect Python 3.11+. If missing, print a clear message with the download link and exit — don't
   fail with a stack trace.
2. Create a venv on first run; reuse it afterward.
3. Install from a pinned `requirements.txt`. Show progress. First run may take a minute; say so.
4. Run Alembic migrations; seed the two demo profiles if the database is empty.
5. **Check for Ollama and the default model.** If present, confirm and continue. If absent, print
   a friendly note that AI features are off until it's installed (with the install link and the
   `ollama pull` command) — and continue launching. The model is optional at launch; the app is
   not allowed to fail to start over it. Never auto-download multi-GB models without asking.
6. Start uvicorn on `127.0.0.1:8787`, falling back through 8788–8799 if taken.
7. Poll `/health` until ready.
8. **Open the browser in app mode** — `chrome --app=http://127.0.0.1:8787` or the Edge equivalent
   when available, so it opens as a clean window without browser chrome. Fall back to a normal tab
   via `webbrowser.open()`.
9. Keep a console window open showing logs, with a clear "Close this window to quit Meridian" line.
10. Handle Ctrl-C and window close gracefully.

The frontend must be **prebuilt into `app/static` before zipping**. Node is a build-time dependency
only, never a runtime one.

**Stretch (only after everything else is done):** a PyInstaller one-file binary that removes the
Python prerequisite. Nice to have, not required. Don't let it eat time.

---

## 16. Build order

Report at each checkpoint. Don't run ahead.

| # | Milestone | Checkpoint |
|---|---|---|
| 1 | Repo scaffold, folder structure, config, `.env.example`, health endpoint | Server starts, `/health` returns 200 |
| 2 | Data model + Alembic migrations | Schema created, migrations reversible |
| 3 | Auth + profiles + isolation test | Isolation test passes |
| 4 | Mock data generator + all documents | `sample_data/` populated, `DATASET_GUIDE.md` written |
| 5 | Statement parsers (PDF, CSV, OFX) + ingestion pipeline | All 90+ sample documents parse correctly |
| 6 | Provider layer + MockProvider + sync + SSE | Live updates visibly land in a browser |
| 7 | Design system implementation + shell + navigation | Tokens applied, all five states scaffolded |
| 8 | Dashboard, Accounts, Transactions, Documents | Real data rendering, no placeholders |
| 9 | Local model setup + categorization (rules → LLM) + learning loop | Ambiguous merchants land in review, corrections persist |
| 10 | Reconciliation engine + findings + narration | All 13 planted events in §9 are detected |
| 11 | Coach + tool use (local model) | Answers grounded in real queries, shows sources, ≤4 tool calls |
| 12 | Budgets + simulator | Projections use real historical distribution |
| 13 | Error handling, validation, responsive pass, a11y pass | Quality floor met throughout |
| 14 | Packaging, launcher, zip, README | Clean-machine test passes |
| 15 | Assignment deliverables | §18 complete |

---

## 17. Testing

- `pytest` for services, parsers, dedupe, reconciliation matching, and isolation
- **Golden-file tests for every parser** against the generated sample documents
- A test asserting all 13 planted events from §9 are detected
- `vitest` for frontend logic; at minimum smoke-render every route
- A **clean-machine test**: extract the zip to a fresh directory with no venv and confirm the
  launcher works start to finish. Document the result.

---

## 18. Assignment deliverables

Maintain these **as you build**, not at the end. They're graded.

### `docs/PROMPT_LOG.md`
Every prompt I give you, timestamped, with a one-line note on what it produced and whether it
worked first try. The report asks which prompts were most helpful, and I can't reconstruct that
later.

### `docs/DEV_REPORT.md` (1–2 pages)
Draft it progressively. Must cover:
- Which AI assistant and prompts were used
- How this approach differed from App #1 (GridPilot)
- The most helpful prompts
- Key features implemented and how AI helped
- Challenges encountered and how they were solved
- Comparison: building App #1 vs. App #2 — what was easier or faster, and why
- Time spent
- **The local-model decision.** My submitted Workshop 5.2 architecture specified the Claude API;
  the built app defaults to a fully local model for privacy, with the cloud provider retained
  behind the same interface. Write this up as a deliberate architecture evolution driven by the
  sensitivity of financial data — it's a strength of the report, not a discrepancy to hide.

### `docs/TIME_LOG.md`
Running log of time per milestone. Feeds the report's time-spent section.

### `docs/DECISIONS.md`
Every judgment call you make that this brief didn't specify, with the reasoning. This is where the
SQLite-vs-Postgres tradeoff (§5) gets recorded, among others.

### `docs/SCREENSHOT_GUIDE.md`
The assignment requires two screenshots **with visible date and time**:
1. The completed project code in the IDE
2. The app running on localhost in a browser

Tell me exactly what to have on screen for each and how to make the system clock visible.

### `README.md`
Professional: what it is, prerequisites, install, run, environment variables, project structure,
how to load the sample data, how to enable AI features, troubleshooting.

The assignment also explicitly grades: clean folder structure, professional README, environment
variable setup, and error handling throughout. Treat those as rubric items, not niceties.

---

## 19. Lessons from App #1 to apply

GridPilot's failures, and what to do differently:

1. **It simulated its core feature.** Keyword scoring stood in for retrieval, and the app couldn't
   grow past the demo. → Here, every feature is real or explicitly labeled unimplemented.
2. **No backend meant no data integrity.** State lived in components and evaporated. → Real
   persistence, real migrations, real transactions from milestone 2.
3. **Business logic lived in components.** Changing anything meant changing the UI. → Strict
   layering (§6). Services return domain objects.
4. **Error handling was an afterthought.** Failures showed blank screens. → All five states on
   every view, from the moment each view is built.
5. **Config was hardcoded.** → `.env` from milestone 1, `.env.example` committed, nothing secret in
   the repo.
6. **No tests.** Every change was a gamble. → Tests alongside features, especially parsers and
   reconciliation.
7. **The design was assembled from defaults.** → §13 is a real design brief. Follow it.

---

## 20. Open questions

Answer these in `docs/BUILD_PLAN.md`; flag anything you need me to decide.

1. Confirm `qwen2.5:7b-instruct` as the default local model, or propose an alternative with
   function-calling evidence and a hardware-based recommendation for my machine.
2. Proposed approach for matching provider transactions to statement transactions across 1–3 day
   date shifts without generating false positives.
3. Whether the review queue should support bulk category application by merchant pattern in
   Iteration 1, or whether that's Iteration 2.
4. Any place where this brief is internally inconsistent — tell me rather than picking silently.

---

## 21. Working style

- Work in milestones. Report at each checkpoint with what's done, what's next, and anything that
  surprised you.
- Show me the design plan and the build plan before building on top of them.
- Screenshot the UI as you build and critique your own work against §13.
- If something in this brief is wrong or would produce a worse app, say so. I'd rather argue about
  it now than find out at milestone 14.
