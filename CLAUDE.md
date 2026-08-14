# Working on Meridian

Read this before changing anything. It records the rules the codebase already follows —
breaking one of them silently is the failure mode that costs the most time here.

## Getting a working environment

Web sessions run `.claude/hooks/session-start.sh` automatically (virtualenv + frontend
deps). Locally:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd frontend && npm install
```

Always run Python through `.venv/bin/python`. The repo has a directory called `alembic/`,
so a bare `python -m alembic` from the repo root resolves the *directory* instead of the
package unless the real one is importable.

## Commands

| Task | Command |
| --- | --- |
| Backend tests (161) | `.venv/bin/python -m pytest -q` |
| Frontend tests (13) | `cd frontend && npm test` |
| Type check | `cd frontend && npx tsc -b` |
| Run the app locally | `.venv/bin/python launcher.py` (or `./start.sh`) |
| Migrations | `.venv/bin/python -m alembic upgrade head` |
| New migration | `.venv/bin/python -m alembic revision -m "…"` — write it by hand, autogenerate is not wired up |
| Reseed demo profiles | `.venv/bin/python scripts/seed_demo.py` (idempotent) |
| Factory reset | `rm -rf data/` |
| Release zip | `.venv/bin/python scripts/build_zip.py` |

## The rules that are not negotiable

These come from the project brief and are enforced by tests. Changing one is a decision to
document in `docs/DECISIONS.md`, not a refactor.

1. **Money is never a float.** Integer minor units (cents) in the database and in every
   calculation; format only at the edge. Columns are `*_minor`.
2. **Every query is scoped by `user_id`.** Repositories take it as a parameter and filter
   on it. `tests/test_isolation.py` and `tests/test_repo_signatures.py` enforce this
   structurally — if you add a repository method, it needs `user_id`.
3. **The AI layer never leaves the machine.** `LLMProvider` talks to a loopback endpoint,
   and a startup check verifies the configured URL resolves to `127.0.0.1`. There is no
   configuration that turns this off; the Anthropic provider is off unless an explicit key
   is set, and the UI says so. Do not add an outbound call in an AI code path.
4. **Judgment in the model, guarantees in code.** Anything the model produces that must be
   correct — totals, confidence ceilings, category identifiers — is computed or clamped in
   Python after the model answers. Prompts do not get to be the guarantee.
5. **Layering.** Routers do no business logic, services do no SQL, repositories do no HTTP.
   Services return domain dataclasses (`app/domain/`), not ORM models.
6. **No fake functionality.** If something isn't implemented or a dependency is missing,
   the UI says so plainly rather than showing a plausible-looking empty state.
7. **Nothing secret in the repo.** Configuration comes from the environment with working
   defaults; `.env.example` documents every value.

## Frontend changes need a rebuild

`app/static/` holds the **built** React app and is committed — that is what makes the
download and the container work without Node. After any change under `frontend/`:

```bash
cd frontend && npm run build     # writes ../app/static
```

and commit the result. Forgetting this ships a UI that silently doesn't include your
change. Three of this project's worst bugs were packaging bugs of exactly this shape, so
when you touch the frontend, check `app/static/assets/` actually changed before committing.

## Deploying

`git push` to `main`, then redeploy (see `docs/DEPLOY.md`):

```bash
gcloud run deploy meridian --source . --region us-central1
```

The Dockerfile builds the seeded database at image-build time, so `serve.py` copies it into
place instead of migrating on each cold start. If you change the schema or the seed script,
nothing extra is needed — the next image build picks it up.

## Conventions

- Comments explain *why*, not *what*, and are sparse. Match the surrounding density.
- Tests are named for the behaviour they protect, and bug-fix tests carry a one-line
  comment saying which bug they exist for.
- Every non-obvious decision goes in `docs/DECISIONS.md` as the next `D-0xx`, with the
  reasoning, not just the outcome.
- British-influenced plain prose in docs; no marketing voice, no emoji.
