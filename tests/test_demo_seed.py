"""The demo profiles: what the seeder promises, and what makes it portable.

The demo data is built once — inside the container image, inside the release zip —
and opened somewhere else, so the two things that break silently are stored paths
that only exist on the build machine, and a ground-truth fill that quietly swallows
the transactions the review queue is supposed to show.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n"
)


async def test_uploaded_documents_record_a_relative_path(client, tmp_path):
    """An absolute path recorded at build time points at nothing on the machine that
    later opens the database — which is every machine, for the demo profiles."""
    from sqlalchemy import select

    from app.core.db import get_session_factory
    from app.models import Document

    await client.post("/api/auth/register", json={
        "display_name": "Path Tester", "email": "paths@example.com",
        "password": "path-tester-123"})
    sample = (PROJECT_ROOT / "sample_data" / "jordan" / "statements" / "american_bank"
              / "checking_4417_2025-11.pdf")
    resp = await client.post("/api/documents/upload", files=[
        ("files", (sample.name, sample.read_bytes(), "application/pdf"))])
    assert resp.json()[0]["status"] == "uploaded", resp.json()

    async with get_session_factory()() as session:
        (stored,) = list(await session.scalars(select(Document.stored_path)))
    assert not Path(stored).is_absolute(), stored
    assert stored.startswith("1/documents/"), stored


def test_stored_paths_resolve_against_the_current_data_directory(monkeypatch, tmp_path):
    from app.core.config import get_settings
    from app.services.ingestion import resolve_stored_path

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    try:
        assert resolve_stored_path("1/documents/x.pdf") == tmp_path / "1/documents/x.pdf"
        # Rows written before paths were stored relative still resolve.
        assert resolve_stored_path("/somewhere/else/x.pdf") == Path("/somewhere/else/x.pdf")
        assert resolve_stored_path(None) is None
    finally:
        get_settings.cache_clear()


def test_ground_truth_fill_leaves_the_review_queue_something_to_do():
    """The cryptic descriptors exist to be triaged. Pre-filling them from the
    generator would delete the feature they were built to demonstrate."""
    from mockgen import jordan as jordan_gen

    from scripts.seed_demo import ground_truth_categories

    truth = ground_truth_categories("jordan")
    assert truth, "no ground truth recovered"
    assert not (set(truth) & set(jordan_gen.AMBIGUOUS)), \
        "ambiguous descriptors must stay uncategorized"
    assert "Uncategorized" not in truth.values()
    # And it covers the ordinary merchants, or the Budgets screen stays empty.
    assert len(truth) > 100


def test_demo_credentials_match_the_profiles_the_seeder_creates():
    """Two lists of demo passwords would drift; there is one."""
    from app.core.demo import DEMO_BLURBS, DEMO_CREDENTIALS

    from scripts.seed_demo import DEMO_PROFILES

    emails = {email for _, email, _ in DEMO_PROFILES}
    assert emails == set(DEMO_CREDENTIALS) == set(DEMO_BLURBS)
