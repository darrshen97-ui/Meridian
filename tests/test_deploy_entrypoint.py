"""The Cloud Run entry point.

Deployment code is the part of this project that local test runs never
exercise, which is exactly where its three worst bugs have lived. These tests
cover the start-up decision itself: use the database baked into the image, or
build one.
"""
from __future__ import annotations

import sqlite3

import pytest

import serve


def _baked(tmp_path):
    """Stand in for the database the Dockerfile builds at /app/seed."""
    path = tmp_path / "seed" / "meridian.db"
    path.parent.mkdir(parents=True)
    sqlite3.connect(path).close()
    return path


def test_baked_database_is_copied_instead_of_rebuilt(tmp_path, monkeypatch):
    target = tmp_path / "run" / "meridian.db"
    monkeypatch.setattr(serve, "BAKED_DB", _baked(tmp_path))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:////{target.as_posix().lstrip('/')}")
    monkeypatch.setattr(
        serve, "run", lambda *a: pytest.fail("rebuilt despite a baked database"))

    serve.prepare_database()

    assert target.is_file(), "the baked database was not restored"


def test_existing_database_is_left_alone(tmp_path, monkeypatch):
    """A container restart with the file still present must not overwrite it."""
    target = tmp_path / "run" / "meridian.db"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"live data")
    monkeypatch.setattr(serve, "BAKED_DB", _baked(tmp_path))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:////{target.as_posix().lstrip('/')}")

    serve.prepare_database()

    assert target.read_bytes() == b"live data"


def test_without_a_baked_image_it_migrates_and_seeds(tmp_path, monkeypatch):
    """The fallback still has to work: an image built before this optimisation,
    or a future non-SQLite database, gets the original migrate-and-seed path.
    """
    called: list[str] = []
    monkeypatch.setattr(serve, "BAKED_DB", tmp_path / "absent.db")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:////{tmp_path.as_posix().lstrip('/')}/x.db")
    monkeypatch.setattr(serve, "run", lambda label, argv: called.append(label))

    serve.prepare_database()

    assert called == ["applying database migrations", "seeding demo profiles"]
