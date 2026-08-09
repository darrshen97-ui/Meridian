# Prompt Log — Meridian Financial

Every prompt given to Claude Code, timestamped, with a one-line note on what it produced and
whether it worked first try. (Required deliverable, brief §18.)

| # | Date (2026) | Prompt (condensed) | Produced | First try? |
|---|---|---|---|---|
| 1 | Aug 9 | Attached `CLAUDE_CODE_BRIEF.md`: "Read the brief in full, then produce `docs/BUILD_PLAN.md` before writing any code. New project, stored completely separately in GitHub and cloud container." | Full build plan (`docs/BUILD_PLAN.md`), decisions log seeded (D-000…D-006), this log, time log skeleton. Answered all four §20 open questions and flagged 6 internal inconsistencies in the brief. | Mostly — the plan itself yes; creating the separate GitHub repo was blocked by integration permissions (403), so work is parked on an orphan branch pending manual repo creation. |
| 2 | Aug 9 | "I opened another repo called meridian" | Migrated all project files from the GridPilot-AI parking branch into `darrshen97-ui/meridian` (now the permanent home); deleted the parking branch; updated D-000 and this log. | Yes. |
| 3 | Aug 9 | "Build" | Milestones 1–3: FastAPI scaffold + `/health`; all 14 tables as SQLAlchemy models with reversible Alembic migration; Argon2id auth with JWT cookie; user-scoped repositories; 12 pytest tests passing including the profile-isolation proof and a structural test that every repository method requires `user_id`. Vite/React/Tailwind scaffold builds into `app/static` and is served by the backend. | Yes — one hiccup (`alembic init` refused a pre-created directory; wrote the config by hand). |
