"""Milestone 2 checkpoint: migrations create the full schema and are reversible."""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

EXPECTED_TABLES = {
    "users", "institutions", "accounts", "balances", "transactions", "categories",
    "user_corrections", "documents", "budgets", "reconciliations",
    "reconciliation_findings", "sync_runs", "audit_log", "ai_calls",
}


def _alembic(tmp_db: Path, *args: str) -> None:
    env = dict(os.environ, DATABASE_URL=f"sqlite:///{tmp_db}")
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=PROJECT_ROOT, env=env, check=True, capture_output=True,
    )


def _tables(tmp_db: Path) -> set[str]:
    con = sqlite3.connect(tmp_db)
    try:
        rows = con.execute("select name from sqlite_master where type='table'")
        return {r[0] for r in rows} - {"alembic_version", "sqlite_sequence"}
    finally:
        con.close()


def test_migrations_up_down_up(tmp_path):
    db = tmp_path / "mig.db"
    _alembic(db, "upgrade", "head")
    assert _tables(db) == EXPECTED_TABLES
    _alembic(db, "downgrade", "base")
    assert _tables(db) == set()
    _alembic(db, "upgrade", "head")
    assert _tables(db) == EXPECTED_TABLES


def test_schema_matches_models(tmp_path):
    """The migration and the ORM models must agree (no drift)."""
    db = tmp_path / "drift.db"
    _alembic(db, "upgrade", "head")

    from sqlalchemy import create_engine, inspect

    from app.models import Base

    engine = create_engine(f"sqlite:///{db}")
    inspector = inspect(engine)
    for table_name, table in Base.metadata.tables.items():
        model_cols = {c.name for c in table.columns}
        db_cols = {c["name"] for c in inspector.get_columns(table_name)}
        assert model_cols == db_cols, f"drift in {table_name}"
