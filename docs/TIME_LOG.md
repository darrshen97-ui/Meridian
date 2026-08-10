# Time Log — Meridian Financial

Running log of time spent per milestone. Feeds the development report's time-spent section.
(Required deliverable, brief §18.)

| Milestone | Description | Date(s) | Time spent | Notes |
|---|---|---|---|---|
| 0 | Read brief, build plan, decisions log, project setup | Aug 9, 2026 | ~1 h | Repo creation blocked by GitHub App permissions; parked on orphan branch |
| 1 | Scaffold + health endpoint | Aug 9, 2026 | ~45 min | Includes frontend toolchain proof (Vite build → app/static, served by FastAPI) |
| 2 | Data model + Alembic | Aug 9, 2026 | ~40 min | All 14 tables; up/down/up verified; schema-vs-models drift test added |
| 3 | Auth + profiles + isolation test | Aug 9, 2026 | ~50 min | Isolation proven both directions (owner sees data, other profile sees zero) |
| 4 | Mock data generator + documents | Aug 9, 2026 | ~2 h | Largest milestone so far; determinism verified by manifest diff across two runs |
| 5 | Statement parsers + ingestion | Aug 9, 2026 | ~1.5 h | All 117 sample documents parse and cross-check against the ledger exactly |
| 6 | Provider layer + sync + SSE | Aug 9, 2026 | ~1.5 h | Tests caught an account-duplication bug and a sync-reporting flaw; both fixed |
| 7 | Design system + shell | Aug 9, 2026 | ~1 h | Screenshotted light/dark/mobile and critiqued against §13 (docs/screenshots/dev/) |
| 8 | Dashboard / Accounts / Transactions / Documents | Aug 9, 2026 | ~2 h | Live SSE update and upload→preview→import proven in a real browser session |
| 9 | Local model + categorization + learning loop | Aug 9, 2026 | ~2.5 h | Installed real Ollama + qwen2.5:3b in the dev container; tuned prompts against the actual model |
| 10 | Reconciliation engine + narration | Aug 9, 2026 | ~1.5 h | Full-pipeline test: 79 periods reconciled, 3 planted divergences found, zero false positives |
| 11 | Coach + tool use | Aug 9, 2026 | ~2 h | Tested on both real models: 3B exposed 3 weaknesses (fixed deterministically); 7B default answers correctly |
| 12 | Budgets + simulator | Aug 10, 2026 | ~1.5 h | Projection math verified against manual recomputation of the real distribution |
| 13 | Hardening: errors, responsive, a11y | Aug 10, 2026 | ~1 h | 375px verified overflow-free; all 9 routes smoke-rendered by vitest |
| 14 | Packaging + launcher + zip | — | — | |
| 15 | Assignment deliverables | — | — | |
