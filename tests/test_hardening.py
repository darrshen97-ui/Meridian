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


async def test_js_bundle_is_served_as_javascript_not_text(client, monkeypatch):
    """A machine that maps .js to text/plain (common on Windows, via the registry)
    must not be able to make the browser refuse our ES module bundle — which
    renders a blank page with no visible error.
    """
    import mimetypes
    from pathlib import Path

    import app.main as main

    bundles = sorted((main.STATIC_DIR / "assets").glob("*.js"))
    if not bundles:
        import pytest

        pytest.skip("frontend not built in this checkout")

    # Poison the machine's MIME map the way a bad registry entry does...
    monkeypatch.setitem(mimetypes.types_map, ".js", "text/plain")
    assert mimetypes.guess_type("x.js")[0] == "text/plain"

    # ...the served asset must still carry a JavaScript content type.
    asset: Path = bundles[0]
    resp = await client.get(f"/assets/{asset.name}")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/javascript"), \
        resp.headers["content-type"]

    # index.html must be HTML, and the health probe reports the effective type.
    assert (await client.get("/")).headers["content-type"].startswith("text/html")
    assert main.CONTENT_TYPES[".js"] == "text/javascript"


async def test_index_html_is_never_cached(client):
    """index.html names content-hashed bundles; a cached copy points at files
    that no longer exist after a rebuild and the app renders blank."""
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "no-store" in resp.headers.get("cache-control", "")


async def test_login_is_throttled_after_repeated_failures(client):
    """Security audit finding: unlimited password guesses were possible against
    a known email (the demo profiles are published in the README)."""
    from app.services.auth import reset_login_throttle

    reset_login_throttle()
    await client.post("/api/auth/register", json=USER)
    client.cookies.clear()

    for _ in range(8):
        resp = await client.post("/api/auth/login",
                                 json={"email": USER["email"], "password": "wrong"})
        assert resp.status_code == 401

    resp = await client.post("/api/auth/login",
                             json={"email": USER["email"], "password": "wrong"})
    assert resp.status_code == 429
    assert "Too many failed" in resp.json()["detail"]

    # Even the correct password is refused while locked out.
    resp = await client.post("/api/auth/login",
                             json={"email": USER["email"], "password": USER["password"]})
    assert resp.status_code == 429
    reset_login_throttle()
