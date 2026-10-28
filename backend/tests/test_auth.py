from sqlalchemy import select

from app.auth.deps import COOKIE_NAME
from app.db import SessionLocal
from app.models import User

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
LOGOUT = "/api/auth/logout"
ME = "/api/auth/me"

CREDS = {"email": "student@example.com", "password": "secret123"}


def test_register_logs_in(client):
    r = client.post(REGISTER, json=CREDS)
    assert r.status_code == 201
    assert r.json()["email"] == CREDS["email"]
    assert "password" not in r.json() and "password_hash" not in r.json()

    cookie = r.headers["set-cookie"].lower()
    assert COOKIE_NAME in cookie and "httponly" in cookie and "samesite=lax" in cookie

    assert client.get(ME).json()["email"] == CREDS["email"]


def test_password_stored_as_argon2_hash(client):
    client.post(REGISTER, json=CREDS)
    with SessionLocal() as db:
        user = db.scalar(select(User))
    assert user.password_hash != CREDS["password"]
    assert user.password_hash.startswith("$argon2")


def test_register_duplicate_email_case_insensitive(client):
    client.post(REGISTER, json=CREDS)
    r = client.post(REGISTER, json={**CREDS, "email": "Student@Example.COM"})
    assert r.status_code == 409


def test_register_validation(client):
    assert client.post(REGISTER, json={**CREDS, "password": "short"}).status_code == 422
    assert client.post(REGISTER, json={**CREDS, "password": "x" * 129}).status_code == 422
    assert client.post(REGISTER, json={**CREDS, "email": "not-an-email"}).status_code == 422
    assert client.post(REGISTER, json={"email": CREDS["email"]}).status_code == 422


def test_login_ok(client):
    client.post(REGISTER, json=CREDS)
    client.cookies.clear()
    assert client.get(ME).status_code == 401

    r = client.post(LOGIN, json=CREDS)
    assert r.status_code == 200
    assert client.get(ME).json()["email"] == CREDS["email"]


def test_login_wrong_password_and_unknown_email_look_the_same(client):
    client.post(REGISTER, json=CREDS)
    client.cookies.clear()

    wrong_pass = client.post(LOGIN, json={**CREDS, "password": "wrong-pass"})
    unknown = client.post(LOGIN, json={**CREDS, "email": "nobody@example.com"})
    assert wrong_pass.status_code == unknown.status_code == 401
    assert wrong_pass.json() == unknown.json()


def test_logout(client):
    client.post(REGISTER, json=CREDS)
    assert client.post(LOGOUT).status_code == 204
    assert client.get(ME).status_code == 401


def test_me_without_or_with_bad_token(client):
    assert client.get(ME).status_code == 401
    client.cookies.set(COOKIE_NAME, "garbage.token.value")
    assert client.get(ME).status_code == 401


def test_token_for_deleted_user_rejected(client):
    client.post(REGISTER, json=CREDS)
    with SessionLocal() as db:
        db.delete(db.scalar(select(User)))
        db.commit()
    assert client.get(ME).status_code == 401


def test_login_rate_limit(client):
    bad = {**CREDS, "password": "wrong-pass"}
    for _ in range(10):
        assert client.post(LOGIN, json=bad).status_code == 401
    r = client.post(LOGIN, json=bad)
    assert r.status_code == 429
    assert "попыток" in r.json()["detail"]
