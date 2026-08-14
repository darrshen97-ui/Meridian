#!/bin/bash
# Prepare a fresh Claude Code on the web container: Python virtualenv with the
# pinned runtime and test dependencies, and the frontend toolchain. Without this
# a session starts with no way to run the 161 tests or rebuild the interface.
set -euo pipefail

# Local machines already have their environment; this is for remote sessions.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

echo "[session-start] python dependencies"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt

echo "[session-start] frontend dependencies"
if [ -d frontend ]; then
  (cd frontend && npm install --no-audit --no-fund --loglevel=error)
fi

# Tests and scripts must use the virtualenv, not the system interpreter:
# `python -m alembic` from the repo root resolves the ./alembic *directory*
# unless the real package is importable.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export PATH=\"$PWD/.venv/bin:\$PATH\""
    echo "export VIRTUAL_ENV=\"$PWD/.venv\""
  } >> "$CLAUDE_ENV_FILE"
fi

echo "[session-start] ready — pytest for the backend, npm test in frontend/"
