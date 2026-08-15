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


async def test_profiles_list_exposes_nothing_about_a_real_profile(client):
    """The welcome screen is pre-auth. A profile someone created gets a name and
    nothing else — in particular the demo-credential fields stay empty, or the
    convenience for the demo accounts would become a password leak for everyone."""
    await client.post("/api/auth/register", json=A)
    client.cookies.clear()
    resp = await client.get("/api/auth/profiles")
    assert resp.status_code == 200
    (profile,) = resp.json()
    assert set(profile.keys()) == {"id", "display_name", "email",
                                   "demo_password", "demo_blurb"}
    assert profile["demo_password"] is None
    assert profile["demo_blurb"] is None


async def test_seeded_demo_profiles_publish_their_own_password(client):
    """Their credentials are in the README and the dataset guide; the sign-in screen
    fills them in so a first-time visitor can get in without hunting for them."""
    from app.core.demo import DEMO_CREDENTIALS

    email, password = next(iter(DEMO_CREDENTIALS.items()))
    await client.post("/api/auth/register",
                      json={"display_name": "Demo", "email": email,
                            "password": password})
    client.cookies.clear()

    (profile,) = (await client.get("/api/auth/profiles")).json()
    assert profile["demo_password"] == password
    assert profile["demo_blurb"]

    # And the password it publishes actually works.
    resp = await client.post("/api/auth/login",
                             json={"email": email, "password": profile["demo_password"]})
    assert resp.status_code == 200
