async def test_health_returns_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "meridian"


async def test_protected_endpoints_require_auth(client):
    for path in ["/api/accounts", "/api/transactions", "/api/institutions",
                 "/api/documents", "/api/categories", "/api/budgets", "/api/auth/me"]:
        resp = await client.get(path)
        assert resp.status_code == 401, path
