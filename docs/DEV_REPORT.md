# Development Report — Meridian Financial (App #2)

Workshop 5.3 · Iteration 1 · August 9–10, 2026

## Assistant and approach

Meridian was built with **Claude Code** (Anthropic), working from a single authoritative
build brief (`docs/CLAUDE_CODE_BRIEF.md`). The workflow was deliberately different from
App #1: instead of prompting screen by screen, I wrote the full specification first —
scope, data model, design system, a 15-milestone build order, and a set of non-negotiables
— and required a written build plan (`docs/BUILD_PLAN.md`) before any code. Claude Code
then built one milestone per prompt, stopping at each checkpoint with test evidence.
Every prompt is logged in `docs/PROMPT_LOG.md`; every judgment call the brief didn't
specify is recorded with reasoning in `docs/DECISIONS.md` (23 entries, D-000–D-022).

## Most helpful prompts

The single most valuable prompt was the brief itself — front-loading the specification
meant nearly every "build" prompt worked close to first try. Three ideas inside it paid
off repeatedly:

1. **"Produce `docs/BUILD_PLAN.md` before writing any code"** — surfaced six internal
   inconsistencies in my own spec (e.g. the schema had no account type for the Fidelity
   brokerage; §14 required bulk-apply while §20 asked whether to defer it) before they
   became bugs.
2. **The planted-events dataset spec (§9)** — 13 known anomalies generated into the mock
   data gave every later feature a testable target. The milestone-10 checkpoint test
   imports all 117 sample documents, reconciles 79 statement periods, and asserts the
   *only* actionable findings are the 3 planted divergences — zero false positives.
3. **"Test every prompt against the actual model"** — Claude Code installed a real Ollama
   with qwen2.5 (3B and 7B) inside its own dev container and iterated the prompts against
   them, which found real failures no mock would have (below).

## Key features and how AI helped

All five product features are functional end to end: dashboard with spending power,
statement ingestion (PDF/CSV/OFX with preview-before-import), live sync over SSE with a
mock provider, two-pass categorization with a review queue and learning loop,
reconciliation with plain-language narration, a tool-using spending coach, and a budget
simulator. The AI assistant wrote effectively all code and tests (154 pytest + 13 vitest),
but the tests repeatedly caught its own bugs — sync duplicating statement-created
accounts (D-014), balance failures silently discarding ingested-row counts (D-015) —
which is precisely why tests were built alongside features rather than after.

## Challenges and how they were solved

- **Small local models are confidently wrong.** The 3B auto-applied wrong categories to
  cryptic processor descriptors at exactly the 0.8 threshold, and both models misreported
  precomputed dollar totals in prose. The pattern that solved every instance: *judgment in
  the model, guarantees in code* — a deterministic confidence cap on cryptic descriptors
  (D-017), tool-computed totals printed by the UI regardless of model prose (D-020), and
  handing the model every derived figure so it has nothing to compute (D-021).
- **PDF text extraction ate the `••` account masks** (they extract as `(cid:127)`),
  which would have silently broken parser account-matching. Caught at milestone 4 by
  reading the generated PDFs back; fixed with ASCII masks (D-010).
- **Cross-format identity.** Statement, OFX, and provider rows describing the same
  transaction had to collapse into one row without ever collapsing two genuinely
  identical purchases. One shared two-layer matcher (exact occurrence-aware hash +
  amount-exact ±3-day one-to-one assignment) serves import dedupe and reconciliation
  (D-012); the planted date-shift trio matches silently while the planted duplicate is
  still flagged.

## The local-model decision

My submitted Workshop 5.2 architecture specified the Claude API. The built app defaults
to a **fully local model** (Ollama, `qwen2.5:7b-instruct`) — a deliberate architecture
evolution, not a discrepancy. The app processes real financial data; under the built
design no transaction, balance, or merchant name can leave the machine: the AI layer
refuses any endpoint that doesn't resolve to loopback, and every model call is logged to
an `ai_calls` table visible in Settings. The cloud provider survives behind the same
`LLMProvider` interface, off by default and labeled as off-device — so the course
architecture is retained while the product default is private. The measured cost of that
choice: a local model sends more transactions to the review queue and needs deterministic
guardrails around numbers; the review queue was designed as a feature (and the engine of
the learning loop) for exactly this reason.

## App #1 vs App #2

GridPilot (App #1) was a frontend-only prototype whose core feature was simulated and
whose state evaporated on reload. Meridian inverted every one of those lessons: a real
backend with migrations from milestone 2, strict layering (routers → services →
repositories), all five UI states on every view, config via environment from milestone 1,
and tests beside every feature. Counterintuitively, App #2 was *faster per feature*
despite being enormously larger: the up-front brief eliminated the re-prompting cycles
that dominated App #1, and the deterministic sample dataset meant correctness was checkable
by machine instead of by eyeballing. The single biggest difference in experience: with
App #1, I discovered problems by clicking around; with App #2, the test suite usually
found them before I ever saw the screen.

## Time spent

About **22 hours of Claude Code session time over two days** (per-milestone detail in
`docs/TIME_LOG.md`). The heaviest milestones were the mock dataset generator (~2 h) and
the local-model integration with real-model prompt testing (~2.5 h).
