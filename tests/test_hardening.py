"""Milestone 13: error handling and validation floor."""
from __future__ import annotations

USER = {"display_name": "Harden Tester", "email": "harden@example.com",
        "password": "harden-pass-123"}


async def test_unknown_api_route_is_404_json_not_html(client):
    await client.post("/api/auth/register", json=USER)
    resp = await client.get("/api/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["detail"]


async def test_validation_errors_are_structured_422(client):
    await client.post("/api/auth/register", json=USER)
    resp = await client.get("/api/transactions", params={"date_from": "not-a-date"})
    assert resp.status_code == 422
    assert "detail" in resp.json()

    resp = await client.post("/api/simulate", json={"adjustments": []})
    assert resp.status_code == 422

    resp = await client.post("/api/coach/ask", json={"question": ""})
    assert resp.status_code == 422


async def test_oversized_upload_rejected_specifically(client):
    await client.post("/api/auth/register", json=USER)
    big = b"%PDF-1.4 " + b"0" * (16 * 1024 * 1024)
    resp = await client.post("/api/documents/upload",
                             files=[("files", ("huge.pdf", big, "application/pdf"))])
    (result,) = resp.json()
    assert result["status"] == "rejected"
    assert "15 MB" in result["error"]


async def test_unhandled_errors_do_not_leak_internals(client, monkeypatch):
    from app.services import dashboard

    async def boom(self, user_id, today=None):
        raise RuntimeError("secret internal detail: /etc/nothing")

    monkeypatch.setattr(dashboard.DashboardService, "overview", boom)
    await client.post("/api/auth/register", json=USER)
    resp = await client.get("/api/dashboard")
    assert resp.status_code == 500
    body = resp.json()
    assert "secret internal detail" not in str(body)
    assert "server log" in body["detail"]
