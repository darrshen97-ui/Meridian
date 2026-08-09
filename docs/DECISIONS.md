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
