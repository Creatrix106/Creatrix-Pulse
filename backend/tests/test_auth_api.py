from datetime import timedelta

from app.db.base import utcnow
from app.db.models import AuthSession, User
from app.db.session import get_sessionmaker
from sqlalchemy import update

from tests.conftest import new_client, register

CREDENTIALS = {"name": "Asha Verma", "email": "Asha@Example.com", "password": "Passw0rdOK"}


async def test_register_creates_admin_and_httponly_session_cookie(anon):
    response = await anon.post("/api/auth/register", json=CREDENTIALS)
    assert response.status_code == 201
    user = response.json()
    assert set(user) == {"id", "name", "email", "role"}  # exactly the frontend's `User` type
    assert user["email"] == "asha@example.com"  # normalised
    assert user["role"] == "admin" and user["name"] == "Asha Verma"
    assert "password" not in response.text

    cookie = response.headers["set-cookie"].lower()
    assert cookie.startswith("cp_session=")
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie and "max-age=" in cookie
    assert "secure" not in cookie  # the test environment is plain http

    me = await anon.get("/api/auth/me")
    assert me.status_code == 200 and me.json() == user


async def test_register_rejects_duplicate_email_case_insensitively(anon):
    assert (await anon.post("/api/auth/register", json=CREDENTIALS)).status_code == 201
    again = await anon.post("/api/auth/register", json={**CREDENTIALS, "email": "ASHA@example.COM"})
    assert again.status_code == 409
    assert again.json()["code"] == "email_taken"


async def test_register_validation_messages_match_the_frontend_rules(anon):
    cases = [
        ({"password": "short1"}, "Password must be at least 8 characters."),
        ({"password": "nodigitshere"}, "Include at least one number."),
        ({"email": "not-an-email"}, "Enter a valid email address."),
        ({"name": "A"}, "Enter your full name."),
    ]
    for override, message in cases:
        response = await anon.post("/api/auth/register", json={**CREDENTIALS, **override})
        body = response.json()
        assert response.status_code == 422, override
        assert body["code"] == "validation_error" and body["message"] == message, body
        assert body["details"][0]["field"] in {"password", "email", "name"}


async def test_wrong_password_and_unknown_email_are_indistinguishable(anon):
    await anon.post("/api/auth/register", json=CREDENTIALS)
    wrong = await anon.post("/api/auth/login", json={"email": CREDENTIALS["email"], "password": "WrongPass1"})
    unknown = await anon.post("/api/auth/login", json={"email": "nobody@example.com", "password": "WrongPass1"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"code": "invalid_credentials", "message": "Incorrect email or password."}


async def test_login_and_logout_round_trip(app, anon):
    await anon.post("/api/auth/register", json=CREDENTIALS)
    async with new_client(app) as other_device:
        login = await other_device.post("/api/auth/login", json={"email": "asha@example.com", "password": "Passw0rdOK"})
        assert login.status_code == 200 and login.json()["email"] == "asha@example.com"
        token = other_device.cookies["cp_session"]
        assert (await other_device.get("/api/auth/me")).status_code == 200

        logout = await other_device.post("/api/auth/logout")  # body-less POST, like the frontend
        assert logout.status_code == 204 and logout.content == b""
        assert "cp_session" not in other_device.cookies  # cookie cleared
        assert (await other_device.get("/api/auth/me")).json()["code"] == "not_authenticated"

        # the revoked token itself is dead, not merely forgotten by the browser
        replay = await other_device.get("/api/auth/me", headers={"Cookie": f"cp_session={token}"})
        assert replay.status_code == 401 and replay.json()["code"] == "session_expired"
    assert (await anon.get("/api/auth/me")).status_code == 200  # the other session is unaffected


async def test_account_locks_after_repeated_failures(anon):
    await anon.post("/api/auth/register", json=CREDENTIALS)
    for _ in range(5):  # LOGIN_MAX_FAILED_ATTEMPTS=5 in the test environment
        r = await anon.post("/api/auth/login", json={"email": "asha@example.com", "password": "WrongPass1"})
        assert r.status_code == 401
    locked = await anon.post("/api/auth/login", json={"email": "asha@example.com", "password": "Passw0rdOK"})
    assert locked.status_code == 429 and locked.json()["code"] == "too_many_attempts"
    assert int(locked.headers["retry-after"]) > 0


async def test_expired_and_inactive_sessions_are_rejected(client):
    async with get_sessionmaker()() as session:
        await session.execute(update(AuthSession).values(expires_at=utcnow() - timedelta(minutes=1)))
        await session.commit()
    expired = await client.get("/api/auth/me")
    assert expired.status_code == 401 and expired.json()["code"] == "session_expired"


async def test_deactivated_user_cannot_use_or_start_a_session(app, anon):
    await anon.post("/api/auth/register", json=CREDENTIALS)
    async with get_sessionmaker()() as session:
        await session.execute(update(User).values(is_active=False))
        await session.commit()
    assert (await anon.get("/api/auth/me")).status_code == 401
    async with new_client(app) as fresh:
        login = await fresh.post("/api/auth/login", json={"email": "asha@example.com", "password": "Passw0rdOK"})
        assert login.status_code == 401


async def test_protected_routes_require_a_session(anon):
    for method, path in [
        ("GET", "/api/datasets"),
        ("GET", "/api/datasets/abc"),
        ("DELETE", "/api/datasets/abc"),
        ("GET", "/api/datasets/abc/analytics/overview"),
        ("GET", "/api/datasets/abc/reports"),
    ]:
        response = await anon.request(method, path)
        assert response.status_code == 401, path
        assert response.json()["code"] == "not_authenticated"


async def test_session_cookie_is_secure_in_production_settings():
    from app.core.config import Settings

    prod = Settings(environment="production", database_url="postgresql://u:p@h/db")
    assert prod.effective_cookie_secure is True and prod.effective_docs_enabled is False
    assert Settings(environment="development").effective_cookie_secure is False


async def test_other_user_sessions_are_isolated(client, other_client):
    assert (await client.get("/api/auth/me")).json()["id"] != (await other_client.get("/api/auth/me")).json()["id"]
    assert register  # (imported helper used by other modules)


async def test_registration_can_be_closed(anon, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "allow_registration", False)
    response = await anon.post("/api/auth/register", json=CREDENTIALS)
    assert response.status_code == 403 and response.json()["code"] == "registration_disabled"
    assert (
        await anon.post("/api/auth/login", json={"email": "a@example.com", "password": "x"})
    ).status_code == 401  # login unaffected
