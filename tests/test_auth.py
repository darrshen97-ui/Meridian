from __future__ import annotations

A = {"display_name": "Alpha", "email": "alpha@example.com", "password": "correct-horse-42"}


async def test_register_login_me_logout(client):
    resp = await client.post("/api/auth/register", json=A)
    assert resp.status_code == 201
    assert resp.json()["display_name"] == "Alpha"
    assert "meridian_session" in resp.cookies

    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "alpha@example.com"

    resp = await client.post("/api/auth/logout")
    assert resp.status_code == 204

    client.cookies.clear()
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401

    resp = await client.post("/api/auth/login",
                             json={"email": A["email"], "password": A["password"]})
    assert resp.status_code == 200


async def test_short_password_rejected(client):
    resp = await client.post("/api/auth/register",
                             json={**A, "email": "b@example.com", "password": "short"})
    assert resp.status_code == 400
    assert "10 characters" in resp.json()["detail"]


async def test_duplicate_email_rejected(client):
    assert (await client.post("/api/auth/register", json=A)).status_code == 201
    resp = await client.post("/api/auth/register", json=A)
    assert resp.status_code == 409


async def test_wrong_password_rejected(client):
    await client.post("/api/auth/register", json=A)
    client.cookies.clear()
    resp = await client.post("/api/auth/login",
                             json={"email": A["email"], "password": "not-the-password"})
    assert resp.status_code == 401


async def test_profiles_list_is_names_only(client):
    await client.post("/api/auth/register", json=A)
    client.cookies.clear()
    resp = await client.get("/api/auth/profiles")
    assert resp.status_code == 200
    (profile,) = resp.json()
    assert set(profile.keys()) == {"id", "display_name", "email"}
