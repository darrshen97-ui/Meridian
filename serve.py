"""Production entry point (Google Cloud Run).

Cloud Run injects PORT and terminates TLS in front of the container, so the app
binds 0.0.0.0 here rather than loopback. Migrations and demo seeding run at
start-up because the container filesystem begins empty on every revision.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from sqlalchemy.engine import make_url

# Prepared during the image build so scale-from-zero is fast (see Dockerfile).
# Holds the seeded database and the demo profiles' stored statement files, which
# the Documents screen serves and reconciliation re-reads.
BAKED_SEED = Path("/app/seed")
BAKED_DB = BAKED_SEED / "meridian.db"


def run(label: str, argv: list[str]) -> None:
    print(f"[startup] {label}", flush=True)
    result = subprocess.run(argv, cwd=os.path.dirname(os.path.abspath(__file__)))
    if result.returncode != 0:
        sys.exit(f"[startup] {label} failed with code {result.returncode}")


def prepare_database() -> None:
    """Copy the pre-seeded data into place, or build it if it isn't baked."""
    url = os.environ.get("DATABASE_URL", "")
    target = Path(make_url(url).database) if url.startswith("sqlite") else None

    if target and BAKED_DB.exists():
        if not target.exists():
            data_dir = Path(os.environ.get("DATA_DIR", target.parent))
            # The whole tree, not just the database: document rows point at stored
            # files, and a Documents screen that 410s on every row is worse than none.
            shutil.copytree(BAKED_SEED, data_dir, dirs_exist_ok=True)
            if not target.exists():  # DATA_DIR and the database can live apart
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(BAKED_DB, target)
            print(f"[startup] restored pre-seeded data to {data_dir}", flush=True)
        return

    run("applying database migrations", [sys.executable, "-m", "alembic", "upgrade", "head"])
    run("seeding demo profiles", [sys.executable, "scripts/seed_demo.py"])


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    prepare_database()

    import uvicorn

    print(f"[startup] serving on 0.0.0.0:{port}", flush=True)
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
