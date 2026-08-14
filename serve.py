"""Production entry point (Google Cloud Run).

Cloud Run injects PORT and terminates TLS in front of the container, so the app
binds 0.0.0.0 here rather than loopback. Migrations and demo seeding run at
start-up because the container filesystem begins empty on every revision.
"""
from __future__ import annotations

import os
import subprocess
import sys


def run(label: str, argv: list[str]) -> None:
    print(f"[startup] {label}", flush=True)
    result = subprocess.run(argv, cwd=os.path.dirname(os.path.abspath(__file__)))
    if result.returncode != 0:
        sys.exit(f"[startup] {label} failed with code {result.returncode}")


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    run("applying database migrations", [sys.executable, "-m", "alembic", "upgrade", "head"])
    run("seeding demo profiles", [sys.executable, "scripts/seed_demo.py"])

    import uvicorn

    print(f"[startup] serving on 0.0.0.0:{port}", flush=True)
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
