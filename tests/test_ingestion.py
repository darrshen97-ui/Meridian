"""Milestone 5 checkpoint part 2 — the ingestion pipeline end to end over HTTP."""
from __future__ import annotations

from pathlib import Path

SAMPLE = Path(__file__).parent.parent / "sample_data"
USER = {"display_name": "Ingest Tester", "email": "ingest@example.com",
        "password": "ingest-pass-123"}

AB_NOV = SAMPLE / "jordan" / "statements" / "american_bank" / "checking_4417_2025-11.pdf"
CHASE_PDF = SAMPLE / "jordan" / "statements" / "chase" / "checking_7734_2025-09.pdf"
CHASE_OFX = SAMPLE / "jordan" / "ofx" / "chase_checking_7734_2025-09.ofx"


async def _register(client):
    resp = await client.post("/api/auth/register", json=USER)
    assert resp.status_code == 201


async def _upload(client, path: Path) -> int:
    with open(path, "rb") as f:
        resp = await client.post("/api/documents/upload",
                                 files=[("files", (path.name, f, "application/pdf"))])
    assert resp.status_code == 200
    (result,) = resp.json()
    assert result["status"] == "uploaded", result
    return result["document"]["id"]


async def test_upload_preview_import_flow(client):
    await _register(client)
    doc_id = await _upload(client, AB_NOV)

    # Preview shows exactly what will be imported; nothing is written yet.
    resp = await client.get(f"/api/documents/{doc_id}/preview")
    assert resp.status_code == 200
    preview = resp.json()
    assert preview["account_hint"]["mask"] == "4417"
    assert any("CHECK #1042" in t["description"] for t in preview["transactions"])
    assert preview["problems"] == []
    assert (await client.get("/api/transactions")).json() == []

    # No account exists yet → the import asks rather than guessing.
    resp = await client.post(f"/api/documents/{doc_id}/import", json={})
    assert resp.status_code == 409
    assert resp.json()["can_create"] is True

    # Confirm with account creation.
    resp = await client.post(f"/api/documents/{doc_id}/import",
                             json={"create_account": True})
    assert resp.status_code == 200
    result = resp.json()
    assert result["imported"] == len(preview["transactions"])
    assert result["merged"] == 0

    rows = (await client.get("/api/transactions", params={"limit": 500})).json()
    assert len(rows) == result["imported"]
    assert all(r["source"] == "statement" for r in rows)
    assert all(r["source_document_id"] == doc_id for r in rows)

    # The document view traces which transactions came from this document.
    linked = (await client.get(f"/api/documents/{doc_id}/transactions")).json()
    assert len(linked) == result["imported"]

    # The created account matched the statement's mask.
    (account,) = (await client.get("/api/accounts")).json()
    assert account["mask"] == "4417"
    docs = (await client.get("/api/documents")).json()
    assert docs[0]["parse_status"] == "parsed"
    assert docs[0]["account_id"] == account["id"]


async def test_exact_reupload_is_rejected(client):
    await _register(client)
    await _upload(client, AB_NOV)
    with open(AB_NOV, "rb") as f:
        resp = await client.post("/api/documents/upload",
                                 files=[("files", (AB_NOV.name, f, "application/pdf"))])
    (result,) = resp.json()
    assert result["status"] == "rejected"
    assert "already uploaded" in result["error"]


async def test_unsupported_format_gets_specific_error(client):
    await _register(client)
    resp = await client.post(
        "/api/documents/upload",
        files=[("files", ("mystery.xyz", b"not a statement", "text/plain"))])
    (result,) = resp.json()
    assert result["status"] == "rejected"
    assert "doesn't match any supported statement format" in result["error"]


async def test_pdf_then_ofx_collapse_via_dedupe(client):
    """The same month via PDF and OFX must merge, not duplicate (D-002)."""
    await _register(client)

    pdf_id = await _upload(client, CHASE_PDF)
    resp = await client.post(f"/api/documents/{pdf_id}/import",
                             json={"create_account": True})
    assert resp.status_code == 200
    imported_pdf = resp.json()["imported"]

    ofx_id = await _upload(client, CHASE_OFX)
    resp = await client.post(f"/api/documents/{ofx_id}/import", json={})
    assert resp.status_code == 200
    result = resp.json()
    assert result["imported"] == 0, "every OFX row should merge with the PDF import"
    assert result["merged"] == imported_pdf

    rows = (await client.get("/api/transactions", params={"limit": 500})).json()
    assert len(rows) == imported_pdf  # no duplicates in the ledger


async def test_documents_are_stored_per_user_on_disk(client, tmp_path):
    await _register(client)
    doc_id = await _upload(client, AB_NOV)
    me = (await client.get("/api/auth/me")).json()
    user_dir = tmp_path / "data" / str(me["id"]) / "documents"
    assert user_dir.exists() and any(user_dir.iterdir()), \
        "uploaded file must live under data/{user_id}/documents/"
    assert doc_id
