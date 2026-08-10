# Decisions Log — Meridian Financial

Every judgment call the brief didn't specify, with reasoning. Newest at the bottom.

---

## D-000 · 2026-08-09 · Repository parking on an orphan branch

**Decision:** Meridian is a new project and must live in its own GitHub repository, but this
session's GitHub integration cannot create repositories and is scoped to `GridPilot-AI` only.
To avoid losing work in an ephemeral environment, Meridian's files are parked on the branch
`claude/new-project-setup-gn7fca` in GridPilot-AI, recreated as an **orphan branch** — it
shares zero history and zero files with GridPilot. Once `darrshen97-ui/meridian-financial`
exists and Claude has access, this branch's content migrates there as the initial commit.

**Why:** Preserves the "completely separate" intent as far as current permissions allow;
nothing was overwritten (the branch previously pointed at the same commit as `main`).

**Resolved 2026-08-09:** `darrshen97-ui/meridian` was created manually and all project files
migrated here. This repository is now Meridian's permanent, separate home; the temporary
parking branch on GridPilot-AI was deleted after migration.

## D-001 · 2026-08-09 · SQLite locally, PostgreSQL-compatible schema (per brief §5)

**Decision:** SQLAlchemy with `DATABASE_URL` from the environment, defaulting to
`sqlite:///data/meridian.db`. The schema is constrained to the intersection of SQLite and
PostgreSQL: no SQLite-specific types, no Postgres-only features (no JSONB, no arrays, no
partial indexes), all migrations via Alembic and portable. Money is `Integer` minor units;
timestamps are timezone-aware UTC stored as ISO strings on SQLite / `timestamptz` semantics on
Postgres via a portable TypeDecorator if needed.

**Why:** The submitted architecture targets PostgreSQL on Cloud SQL, but requiring a Postgres
install would break non-negotiable #3 (zip runs by double-click). Moving to Cloud SQL must be
a config change, not a rewrite. This is a deliberate tradeoff to write up in the development
report: portability costs us Postgres niceties in Iteration 1; it buys a zero-setup local
experience and an unchanged code path at deploy time.

## D-002 · 2026-08-09 · OFX fixtures come from Chase checking ••7734

**Decision:** The brief's "OFX/QFX — one bank, 12 files" doesn't name the bank. Chosen: Chase
checking ••7734, which also has PDF statements.

**Why:** Every bank in the dataset has PDFs, so OFX overlaps one regardless. Making the
overlap deliberate turns it into a test: PDF, OFX, and provider feed describing the same
transactions must collapse via `dedupe_hash` into single rows with all sources recorded.

## D-003 · 2026-08-09 · Date-shift matches are logged as pre-resolved findings

**Decision:** Statement/provider pairs matched across a 1–3 day date shift collapse silently
into one transaction, and a `date_shift` finding is written **already resolved** — visible in
reconciliation detail, never counted as an actionable discrepancy.

**Why:** §9 planted event 13 requires shifted transactions be matched "rather than flagging
false positives", while the §7 schema defines a `date_shift` finding kind. This uses the
schema for transparency without violating the matching requirement.

## D-004 · 2026-08-09 · Mock generator pins "now" to 2026-08-09

**Decision:** `scripts/generate_mock_data.py` uses a fixed reference date (2026-08-09) and a
fixed random seed, never the wall clock.

**Why:** The Aug 1–9, 2026 provider-only tail implies a specific "today". Pinning it keeps
regeneration byte-identical forever, which the golden-file parser tests depend on.

## D-005 · 2026-08-09 · Plain HTTP on loopback; cookie Secure flag off locally

**Decision:** The local app serves HTTP on `127.0.0.1:8787` (no TLS). The JWT cookie is
httpOnly + SameSite=Strict; `Secure` is enabled only in the deployed (Cloud Run) configuration.

**Why:** §6's "HTTPS-to-localhost" isn't achievable in a double-click zip without a
certificate story. Binding exclusively to loopback is the real local security boundary.

## D-006 · 2026-08-09 · System category taxonomy shipped as seed data

**Decision:** ~20 top-level system categories (Income, Housing, Utilities, Groceries, Dining,
Transport, Subscriptions, Insurance, Health, Travel, Shopping, Entertainment, Education, Fees,
Transfers, Crypto, Loan Payments, Cash, Taxes, Uncategorized) seeded with `is_system = true`,
`user_id = NULL`. Users add their own categories beneath them.

**Why:** The brief requires categories but doesn't enumerate them. A fixed system set makes
LLM output validation strict (anything outside the list goes to review) and keeps the two demo
profiles comparable.

## D-007 · 2026-08-09 · Session secret auto-generated and persisted

**Decision:** If `JWT_SECRET` is not set, the app generates one on first run and persists it to
`DATA_DIR/.jwt_secret` (mode 0600 where supported). An explicit env value always wins.

**Why:** The double-click zip must work with zero configuration (non-negotiable #3), but a
random per-boot secret would sign everyone out on every launch. Persisting the generated
secret keeps sessions across restarts with no setup. Deployments set `JWT_SECRET` explicitly.

## D-008 · 2026-08-09 · Enum-like columns are constrained strings, not native enums

**Decision:** Columns like `accounts.type`, `transactions.source`, and finding kinds are
`VARCHAR` with `CHECK` constraints rather than native enum types.

**Why:** Native Postgres `CREATE TYPE` enums are outside the SQLite ∩ PostgreSQL intersection
(D-001) and make additive migrations awkward. Check constraints give the same integrity
portably, and valid values live in one place in `app/models/`.

## D-009 · 2026-08-09 · Added `investment` account type and `brokerage` institution kind

**Decision:** The §7 schema lists account types `checking | savings | credit_card | loan |
crypto | payment_app`, but §9 gives Profile 2 a Fidelity brokerage account and §2/§3 discuss
excluding investments from spending power. Added `investment` to the account-type constraint
and `brokerage` to institution kinds (initial migration regenerated — nothing had shipped).

**Why:** Without it Profile 2 cannot be represented, and spending power's "excludes
investments" rule needs a type to exclude. This is a small internal inconsistency in the
brief (flagged per §20.4).

## D-010 · 2026-08-09 · ASCII account masks in generated documents

**Decision:** Generated statements mask account numbers as `XXXXXX4417` / `*8123` rather
than the `••4417` style used in UI copy.

**Why:** The `•` glyph doesn't survive PDF text extraction cleanly (`(cid:127)` artifacts in
pdfplumber), which would sabotage parser account-matching — and real statements use
ASCII masking anyway. The UI keeps the typographic `••` form.

## D-011 · 2026-08-09 · Dual-source transactions: convention over schema change

**Decision:** When statement and provider data describe the same transaction, the row keeps
its original `source` value and records the second origin through its other columns: a row
with both `external_id` (provider identity) and `source_document_id` (statement identity) is
dual-sourced. No schema change.

**Why:** The brief requires "one row with both sources recorded" but gives `source` a single
value. The two identity columns already encode provenance precisely; the UI derives the
statement/provider/both indicator from them.

## D-012 · 2026-08-09 · Import-time dedupe reuses the reconciliation matcher

**Decision:** `app/services/dedupe.py` implements the two-layer matcher (exact
occurrence-aware hash, then amount-exact ±3-day one-to-one fuzzy assignment) and statement
import runs it against the account's existing rows. The reconciliation engine (milestone 10)
consumes the same module.

**Why:** One matching algorithm, one place, tested once — and importing a PDF after an OFX
(or after provider sync) can never double-book a transaction. OFX truncates descriptions to
32 chars, so the fuzzy layer is genuinely needed, not speculative.

## D-013 · 2026-08-09 · Mock provider identity = email local part

**Decision:** The MockProvider maps a signed-in profile to its fixture by the local part of
the profile's email (`jordan@meridian.demo` → `provider_fixtures/jordan.json`). Profiles
without a fixture sync zero accounts, cleanly.

**Why:** The schema has no provider-credentials table (real credential linking is the Plaid
work deferred to Iteration 2), and demo emails are stable generator outputs. The mapping
lives in one place and disappears when PlaidProvider replaces the mock.

## D-014 · 2026-08-09 · `accounts.provider_key` column (migration 0002)

**Decision:** Added a nullable `provider_key` to accounts, carrying the provider's stable
account identity. Sync upserts by it, and adopts statement-created accounts (matching
mask+type, or type+display-name for maskless accounts) by setting it on first sync.

**Why:** The §7 schema had no provider-side account identity, so incremental sync would have
had to guess by mask every run — and would have duplicated accounts created by statement
imports (a bug the milestone 6 tests actually caught). Migration 0002 is reversible.

## D-015 · 2026-08-09 · Balance-refresh failure does not fail an account's sync

**Decision:** If an account's transactions ingest but its balance fetch exhausts retries, the
account reports `ok` with a `balance_error` note instead of `failed`.

**Why:** The rows are already durably ingested at that point; reporting the account as failed
both lied about the ledger and (before the fix) dropped the ingested rows from the summary.

## D-016 · 2026-08-09 · "Known upcoming obligations" = current credit-card balances

**Decision:** Spending power = latest balances of open liquid accounts (checking, savings,
payment apps) minus current credit-card balances owed. Investments, crypto, and closed
accounts are excluded from the liquid side; loans are excluded from obligations (their
monthly payment is a budget concern, not a balance).

**Why:** §2 defines spending power as liquid capital "minus known upcoming obligations"
without defining the obligations. Card balances are the one deterministic, always-known
obligation the data actually contains. Predicting upcoming bills from recurrence detection
would be a guess — Iteration 2 material. The dashboard states the formula in plain language
under the number so it's never mysterious.

## D-017 · 2026-08-09 · Cryptic-descriptor confidence is capped in code, not prompt

**Decision:** Processor descriptors that hide the real merchant (`SQ *`, `TST*`, `PP*`,
`PAYPAL *`, `POS DEBIT`, …) have their model confidence capped at 0.5 deterministically
after the LLM call. They can only ever auto-apply through the user's own corrections in the
rules pass — never through a model guess.

**Why:** Tested against a real local model (qwen2.5:3b-instruct running in the dev
container). The small model is confidently wrong about these descriptors (`TST* MERIDIAN 04`
→ "Utilities, 0.8"), and packing more calibration rules into the system prompt made it
*more* erratic (it started misfiling obvious subscriptions). The brief's own principle
applies: judgment in the model, hard guarantees in code. The prompt stays short; the
guarantee is deterministic.

## D-018 · 2026-08-09 · Real-model validation ran on the 3B; the 7B stays the default

**Decision:** Development-time prompt testing used `qwen2.5:3b-instruct` (the dev container
is CPU-only; the 7B would be impractically slow there). The shipped default remains
`qwen2.5:7b-instruct` per the build plan, with the 3B offered in Settings and by the
first-use speed test.

**Why:** The 3B is the *worst realistic case* for prompt quality — if the pipeline holds
calibrated behavior on it (ambiguous → review, clear merchants → auto-file), the 7B only
improves from there. Observed on real hardware: ~35-55 s per 15-transaction batch on CPU,
28/63 auto-applied, 35/63 correctly held for review, zero hallucinated categories accepted.

## D-019 · 2026-08-09 · Reconciliation identities and balance anchoring

**Decision:** Because statement and provider rows collapse into single rows at import/sync
(D-011/D-012), the engine classifies by identity: statement-identity-only → missing in
provider; provider-identity-only → missing in statement; both identities with dates 1–3 days
apart (second date preserved on `transaction_date` at merge time) → pre-resolved date-shift.
The computed period-ending balance anchors on the latest provider balance snapshot and walks
the ledger backwards, rather than requiring a stored opening balance.

**Why:** The collapsed-ledger design makes matching a one-time event instead of a per-run
recomputation, and the anchor approach needs no schema addition. A useful property falls out:
a statement-only transaction (the planted CHECK #1042) shows up twice, coherently — as a
finding AND as an exact balance delta ($230.00) that the finding explains.

## D-020 · 2026-08-09 · Coach tool use is schema-driven; totals are deterministic

**Decision:** The coach's tool loop is schema-driven (each step the model emits a JSON
decision: call a tool with arguments, or answer) rather than native function-calling. Query
tools precompute totals; the response payload carries those computed totals separately, and
the UI prints "Queried total: … across N transactions" under every answer regardless of the
model's prose. Identical repeated calls are rejected with a corrective note, and a
merchant+category query that matches nothing deterministically retries without the category
filter (uncategorized rows shouldn't hide a merchant search).

**Why:** All of this came from testing against real local models. The 3B repeated identical
queries, gave up instead of widening filters, and twice misreported the tool's precomputed
total in prose ($743.39, then $689.34, for a true $943.39). The 7B default answered
correctly ($943.39, one tool call) — but the UI's deterministic total line means even a
small model's prose slip can never show the user a wrong number unaccompanied by the right
one. Math in code, language in the model, verification always visible.

## D-021 · 2026-08-10 · Every figure the model may mention is precomputed

**Decision:** Wherever a model explains numeric results (coach, reconciliation narration,
simulation), the facts handed to it include every derived figure it could plausibly want —
monthly deltas AND their cumulative totals — with an explicit "do not compute any other
figures" instruction. The deterministic summary and tables always carry the true numbers
regardless.

**Why:** Observed twice on real models: given a monthly figure and a horizon, even the 7B
multiplied wrong in prose ($296.70 for a true $386.70). If a figure isn't handed over, a
model will derive it — so the fix is to leave it nothing to derive.

## D-022 · 2026-08-10 · Launcher = thin OS wrappers over a stdlib-only launcher.py

**Decision:** `Start Meridian.bat`, `Start Meridian.command`, and `start.sh` only locate a
Python and run `launcher.py`, which uses the standard library exclusively: version check
with a download link, venv creation, pinned install keyed to a requirements hash (reinstall
only when the pin set changes), migrations, idempotent demo seeding, live Ollama/model
detection with the exact enable command, port fallback 8787→8799, health polling, Chrome/
Edge app-mode with plain-browser and print-the-URL fallbacks, graceful Ctrl-C/close.

**Why:** All launch logic in one cross-platform, testable file instead of three divergent
shell dialects — and it must run before any dependency exists, hence stdlib-only.

**Clean-machine test (brief §17), run 2026-08-10 in a fresh directory from the zip with no
venv:** extract → `./start.sh` → private venv created, pinned dependencies installed, three
migrations applied, both demo profiles seeded (2,277 + 1,073 rows), friendly AI-off note
(Ollama absent — the app started anyway, as required), server healthy on 8787 in ~40 s
total. Verified over HTTP: profile list, login, populated dashboard, degraded AI status
with the enable hint, SPA served. Relaunch reused the venv and was up in seconds. The
browser step was skipped via MERIDIAN_NO_BROWSER (headless test container); on a desktop it
opens Chrome/Edge in app mode or any browser as a tab.
