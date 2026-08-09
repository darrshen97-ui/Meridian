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
| 5 | Statement parsers + ingestion | — | — | |
| 6 | Provider layer + sync + SSE | — | — | |
| 7 | Design system + shell | — | — | |
| 8 | Dashboard / Accounts / Transactions / Documents | — | — | |
| 9 | Local model + categorization + learning loop | — | — | |
| 10 | Reconciliation engine + narration | — | — | |
| 11 | Coach + tool use | — | — | |
| 12 | Budgets + simulator | — | — | |
| 13 | Hardening: errors, responsive, a11y | — | — | |
| 14 | Packaging + launcher + zip | — | — | |
| 15 | Assignment deliverables | — | — | |
