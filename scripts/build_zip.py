"""Build the shippable zip: dist/MeridianFinancial-v0.1.zip (brief §15).

Stages exactly what the runtime needs — prebuilt frontend included, Node never
required at runtime — and preserves executable bits for the POSIX launchers.

    python scripts/build_zip.py [--skip-frontend]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
STAGE = DIST / "MeridianFinancial"
ZIP_PATH = DIST / "MeridianFinancial-v0.1.zip"

RUNTIME_ITEMS = [
    "launcher.py",
    "Start Meridian.bat",
    "Start Meridian.command",
    "start.sh",
    "README.md",
    ".env.example",
    "requirements.txt",
    "alembic.ini",
]
EXECUTABLE = {"Start Meridian.command", "start.sh"}


def _copytree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))


def build(skip_frontend: bool) -> None:
    if not skip_frontend:
        print("Building the frontend into app/static …")
        result = subprocess.run(["npm", "run", "build"], cwd=ROOT / "frontend")
        if result.returncode != 0:
            sys.exit("Frontend build failed.")
    if not (ROOT / "app" / "static" / "index.html").exists():
        sys.exit("app/static/index.html is missing — build the frontend first.")

    if not (ROOT / "sample_data" / "DATASET_GUIDE.md").exists():
        print("Generating sample_data …")
        result = subprocess.run([sys.executable,
                                 str(ROOT / "scripts" / "generate_mock_data.py")],
                                cwd=ROOT)
        if result.returncode != 0:
            sys.exit("Sample data generation failed.")

    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    for name in RUNTIME_ITEMS:
        shutil.copy2(ROOT / name, STAGE / name)
    _copytree(ROOT / "app", STAGE / "app")
    _copytree(ROOT / "alembic", STAGE / "alembic")
    _copytree(ROOT / "sample_data", STAGE / "sample_data")
    (STAGE / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts" / "seed_demo.py", STAGE / "scripts" / "seed_demo.py")

    print("Zipping …")
    ZIP_PATH.unlink(missing_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(STAGE.rglob("*")):
            if not path.is_file():
                continue
            arcname = f"MeridianFinancial/{path.relative_to(STAGE)}"
            info = zipfile.ZipInfo(arcname)
            mode = 0o755 if path.name in EXECUTABLE else 0o644
            info.external_attr = mode << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())

    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"Built {ZIP_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-frontend", action="store_true")
    build(parser.parse_args().skip_frontend)
