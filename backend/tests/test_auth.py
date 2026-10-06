from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.security import hash_password, verify_password
from app.models import User
from tests.conftest import COORDINATOR, STUDENT, auth_header

API = "/api/v1"


# ---------- password hashing ----------
def test_password_is_hashed_and_verifiable():
    h = hash_password("Passw0rd123")
    assert h != "Passw0rd123"
    assert verify_password("Passw0rd123", h)
    assert not verify_password("wrong", h)


# ---------- registration ----------
def test_register_student_success(client, db_session):
    res = client.post(f"{API}/auth/register", json=STUDENT)
    assert res.status_code == 201
    body = res.json()
    assert body["token_type"] == "bearer" and body["access_token"]
    assert body["user"]["role"] == "student"
    assert body["user"]["email"] == STUDENT["email"]
    assert "password" not in str(body).lower().replace("passw", "")  # no password fields leaked
    stored = db_session.query(User).one()
    assert stored.password_hash != STUDENT["password"]  # never plaintext
    assert stored.password_hash.startswith("$2")  # bcrypt


def test_register_normalises_email_case(client):
    res = client.post(f"{API}/auth/register", json={**STUDENT, "email": "ASHA@Example.COM"})
    assert res.json()["user"]["email"] == "asha@example.com"


def test_register_duplicate_email_conflict(client):
    client.post(f"{API}/auth/register", json=STUDENT)
    res = client.post(f"{API}/auth/register", json={**STUDENT, "email": "ASHA@example.com"})
    assert res.status_code == 409


@pytest.mark.parametrize(
    "override",
    [
        {"email": "not-an-email"},
        {"password": "short1"},
        {"password": "onlyletters"},
        {"password": "12345678"},
        {"password": "a1" * 40},  # longer than bcrypt's 72 bytes
        {"full_name": "A"},
        {"full_name": ""},
    ],
)
def test_register_validation_errors(client, override):
    res = client.post(f"{API}/auth/register", json={**STUDENT, **override})
    assert res.status_code == 422


def test_register_cannot_choose_coordinator_role(client):
    res = client.post(f"{API}/auth/register", json={**STUDENT, "role": "coordinator"})
    assert res.status_code == 201
    assert res.json()["user"]["role"] == "student"


# ---------- login ----------
def test_login_student_success(client):
    client.post(f"{API}/auth/register", json=STUDENT)
    res = client.post(
        f"{API}/auth/login", json={"email": STUDENT["email"], "password": STUDENT["password"]}
    )
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "student"


def test_login_coordinator_success(client, coordinator):
    res = client.post(
        f"{API}/auth/login",
        json={"email": COORDINATOR["email"], "password": COORDINATOR["password"]},
    )
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "coordinator"


def test_login_wrong_password(client):
    client.post(f"{API}/auth/register", json=STUDENT)
    res = client.post(f"{API}/auth/login", json={"email": STUDENT["email"], "password": "Wrong123x"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password."


def test_login_unknown_email_gives_same_message(client):
    res = client.post(f"{API}/auth/login", json={"email": "nobody@example.com", "password": "Whatever1"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password."


def test_login_invalid_input(client):
    assert client.post(f"{API}/auth/login", json={"email": "bad", "password": "x"}).status_code == 422
    assert client.post(f"{API}/auth/login", json={}).status_code == 422


def test_login_disabled_account(client, db_session):
    client.post(f"{API}/auth/register", json=STUDENT)
    user = db_session.query(User).one()
    user.is_active = False
    db_session.commit()
    res = client.post(
        f"{API}/auth/login", json={"email": STUDENT["email"], "password": STUDENT["password"]}
    )
    assert res.status_code == 403


# ---------- protected routes / tokens ----------
def test_me_requires_token(client):
    res = client.get(f"{API}/auth/me")
    assert res.status_code == 401
    assert res.headers["www-authenticate"] == "Bearer"


def test_me_with_valid_token(client, student_token):
    res = client.get(f"{API}/auth/me", headers=auth_header(student_token))
    assert res.status_code == 200
    assert res.json()["email"] == STUDENT["email"]


def test_garbage_token_rejected(client):
    res = client.get(f"{API}/auth/me", headers=auth_header("not.a.jwt"))
    assert res.status_code == 401


def test_tampered_token_rejected(client, student_token):
    res = client.get(f"{API}/auth/me", headers=auth_header(student_token[:-3] + "abc"))
    assert res.status_code == 401


def test_token_signed_with_other_secret_rejected(client):
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "some-other-secret-that-is-also-long-enough-xx",
        algorithm="HS256",
    )
    assert client.get(f"{API}/auth/me", headers=auth_header(forged)).status_code == 401


def test_expired_token_rejected_with_clear_message(client, student_token):
    secret = "test-secret-key-that-is-long-enough-for-jwt-123456"
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        secret,
        algorithm="HS256",
    )
    res = client.get(f"{API}/auth/me", headers=auth_header(expired))
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


def test_token_for_deleted_user_rejected(client, student_token, db_session):
    db_session.query(User).delete()
    db_session.commit()
    assert client.get(f"{API}/auth/me", headers=auth_header(student_token)).status_code == 401


def test_logout_requires_auth_and_returns_204(client, student_token):
    assert client.post(f"{API}/auth/logout").status_code == 401
    assert client.post(f"{API}/auth/logout", headers=auth_header(student_token)).status_code == 204


# ---------- role-based access ----------
def test_student_can_access_student_route(client, student_token):
    res = client.get(f"{API}/students/me", headers=auth_header(student_token))
    assert res.status_code == 200


def test_student_blocked_from_coordinator_route(client, student_token):
    res = client.get(f"{API}/coordinators/me", headers=auth_header(student_token))
    assert res.status_code == 403


def test_coordinator_can_access_coordinator_route(client, coordinator_token):
    res = client.get(f"{API}/coordinators/me", headers=auth_header(coordinator_token))
    assert res.status_code == 200
    assert res.json()["role"] == "coordinator"


def test_coordinator_blocked_from_student_route(client, coordinator_token):
    res = client.get(f"{API}/students/me", headers=auth_header(coordinator_token))
    assert res.status_code == 403


def test_unauthenticated_blocked_from_role_routes(client):
    assert client.get(f"{API}/students/me").status_code == 401
    assert client.get(f"{API}/coordinators/me").status_code == 401


def test_role_change_applies_immediately(client, student_token, db_session):
    from app.models import Role

    db_session.query(User).one().role = Role.COORDINATOR
    db_session.commit()
    assert client.get(f"{API}/students/me", headers=auth_header(student_token)).status_code == 403


# ---------------------------------------------------------------- limiting password guessing
def _bad_login(client, email, n=1):
    return [client.post(f"{API}/auth/login", json={"email": email, "password": "Wrong123x"}).status_code for _ in range(n)]


def test_repeated_failures_lock_that_email_for_a_while(client):
    client.post(f"{API}/auth/register", json=STUDENT)
    assert _bad_login(client, STUDENT["email"], 5) == [401] * 5
    res = client.post(f"{API}/auth/login", json={"email": STUDENT["email"], "password": STUDENT["password"]})
    assert res.status_code == 429  # even the right password, so guessing cannot continue
    assert "Too many failed login attempts" in res.json()["detail"] and int(res.headers["retry-after"]) > 0


def test_the_lock_is_per_email(client, coordinator):
    client.post(f"{API}/auth/register", json=STUDENT)
    _bad_login(client, STUDENT["email"], 5)
    res = client.post(f"{API}/auth/login", json={"email": COORDINATOR["email"], "password": COORDINATOR["password"]})
    assert res.status_code == 200


def test_a_successful_login_clears_earlier_failures(client):
    client.post(f"{API}/auth/register", json=STUDENT)
    _bad_login(client, STUDENT["email"], 4)
    assert client.post(f"{API}/auth/login", json={"email": STUDENT["email"], "password": STUDENT["password"]}).status_code == 200
    assert _bad_login(client, STUDENT["email"], 4) == [401] * 4  # counting starts again


def test_one_address_cannot_try_many_accounts(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "login_max_failures_per_ip", 6)
    for i in range(6):
        _bad_login(client, f"user{i}@example.com")
    assert _bad_login(client, "someone-else@example.com") == [429]


def test_the_lock_ends_after_the_window(client, monkeypatch):
    from app.core import login_limiter as module

    client.post(f"{API}/auth/register", json=STUDENT)
    clock = [1000.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    _bad_login(client, STUDENT["email"], 5)
    assert _bad_login(client, STUDENT["email"]) == [429]
    clock[0] += 15 * 60 + 1
    assert client.post(f"{API}/auth/login", json={"email": STUDENT["email"], "password": STUDENT["password"]}).status_code == 200


def test_unknown_emails_are_counted_the_same_way(client):
    """Otherwise the difference would reveal which emails are registered."""
    assert _bad_login(client, "nobody@example.com", 6) == [401] * 5 + [429]
