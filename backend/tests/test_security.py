"""Cross-cutting security and error handling: CORS, failures, response headers, and what is never sent back."""
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.database.seed_demo import seed_demo_data
from app.database.session import get_db
from app.main import app
from app.repositories import user_repository
from tests.conftest import COORDINATOR, STUDENT, auth_header

API = "/api/v1"
ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- CORS
def test_cors_allows_the_configured_frontend(client):
    origin = get_settings().cors_origin_list[0]
    res = client.get(f"{API}/health", headers={"Origin": origin})
    assert res.headers["access-control-allow-origin"] == origin


def test_cors_ignores_other_origins(client):
    res = client.get(f"{API}/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in res.headers


def test_cors_preflight_from_another_origin_is_refused(client):
    res = client.options(f"{API}/auth/login", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert res.status_code == 400 and "access-control-allow-origin" not in res.headers


def test_cors_preflight_from_the_frontend_is_allowed(client):
    origin = get_settings().cors_origin_list[0]
    res = client.options(f"{API}/auth/login", headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"})
    assert res.status_code == 200 and res.headers["access-control-allow-origin"] == origin


def test_cors_is_never_a_wildcard():
    assert "*" not in get_settings().cors_origin_list


# ---------------------------------------------------------------- failures
class BrokenSession:
    """A database that is down: every call fails like MySQL being unreachable."""

    def __getattr__(self, name):
        def fail(*args, **kwargs):
            raise OperationalError("SELECT 1", {}, ConnectionRefusedError("MySQL is down"))
        return fail


@pytest.fixture
def broken_db():
    app.dependency_overrides[get_db] = lambda: BrokenSession()
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def test_database_down_gives_a_clear_503_without_details(broken_db):
    res = broken_db.post(f"{API}/auth/login", json={"email": "a@example.com", "password": "whatever123"})
    assert res.status_code == 503
    assert res.json() == {"detail": "The database is temporarily unavailable. Please try again later."}
    assert "MySQL is down" not in res.text and "SELECT" not in res.text


def test_health_reports_the_database_problem_instead_of_crashing(broken_db):
    res = broken_db.get(f"{API}/health")
    assert res.status_code == 200 and res.json()["database"]["connected"] is False
    assert "password" not in res.text.lower()


def test_a_race_on_a_unique_value_is_a_409_not_a_503(client, monkeypatch):
    client.post(f"{API}/auth/register", json=STUDENT)
    monkeypatch.setattr(user_repository, "get_by_email", lambda db, email: None)  # both requests passed the check at once
    res = client.post(f"{API}/auth/register", json=STUDENT)
    assert res.status_code == 409, res.text
    assert res.json() == {"detail": "An account with this email already exists."}


def test_unexpected_error_handler_hides_internals(monkeypatch, db_session):
    from app.services import dashboard_service

    def explode(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(dashboard_service, "build_dashboard", explode)
    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app, raise_server_exceptions=False)
    token = client.post(f"{API}/auth/register", json=STUDENT).json()["access_token"]
    try:
        res = client.get(f"{API}/dashboard", headers=auth_header(token))
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 500
    assert res.json() == {"detail": "Something went wrong on the server. Please try again later."}
    assert "secret internal detail" not in res.text


def test_validation_errors_are_422_with_field_messages(client):
    res = client.post(f"{API}/auth/register", json={"full_name": "", "email": "nope", "password": "1"})
    assert res.status_code == 422 and isinstance(res.json()["detail"], list)


# ---------------------------------------------------------------- headers
def test_security_headers_on_every_response(client):
    for res in (client.get(f"{API}/health"), client.get(f"{API}/jobs"), client.get(f"{API}/nope")):
        assert res.headers["x-content-type-options"] == "nosniff"
        assert res.headers["x-frame-options"] == "DENY"
        assert res.headers["referrer-policy"] == "no-referrer"


# ---------------------------------------------------------------- nothing secret is ever returned
def test_no_response_contains_password_hashes_or_the_jwt_secret(client, db_session, student_token, coordinator_token):
    seed_demo_data(db_session)
    secret = get_settings().jwt_secret_key
    student, coord = auth_header(student_token), auth_header(coordinator_token)
    client.post(f"{API}/applications", headers=student, json={"job_id": 1})
    pages = [
        (student, "/auth/me"), (student, "/students/me"), (student, "/dashboard"), (student, "/applications/me"), (student, "/reports/me"),
        (student, "/recommendations"), (coord, "/auth/me"), (coord, "/coordinators/students"), (coord, "/coordinators/students/1"),
        (coord, "/applications"), (coord, "/coordinators/report"), (coord, "/coordinators/reports/students.csv"), (coord, "/interviews"),
    ]
    for h, path in pages:
        res = client.get(API + path, headers=h)
        assert res.status_code == 200, (path, res.status_code)
        assert "password" not in res.text.lower() and "$2b$" not in res.text and secret not in res.text, path


def test_login_gives_the_same_answer_for_a_wrong_password_and_an_unknown_email(client, coordinator):
    wrong = client.post(f"{API}/auth/login", json={"email": COORDINATOR["email"], "password": "Wrong-pass-123"})
    unknown = client.post(f"{API}/auth/login", json={"email": "nobody@example.com", "password": "Wrong-pass-123"})
    assert wrong.status_code == unknown.status_code == 401 and wrong.json() == unknown.json()


# ---------------------------------------------------------------- secrets stay out of git
def test_secret_files_are_not_tracked_by_git():
    try:
        tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git is not available")
    assert "backend/.env" not in tracked
    assert not [f for f in tracked if f.endswith(".local.sql")]
    assert not [f for f in tracked if f.startswith("backend/uploads/") and not f.endswith(".gitkeep")]


def test_example_settings_contain_no_real_secrets():
    example = (ROOT / "backend" / ".env.example").read_text(encoding="utf-8")
    values = dict(line.split("=", 1) for line in example.splitlines() if "=" in line and not line.startswith("#"))
    assert values["DB_PASSWORD"] == "change_me" and values["JWT_SECRET_KEY"].startswith("replace_with") and values["LLM_API_KEY"] == ""


# ---------------------------------------------------------------- ids
@pytest.mark.parametrize("bad", ["0", "-3", "abc", "1.5", "9223372036854775808"])
def test_an_impossible_id_in_the_url_is_simply_not_found(client, coordinator_token, bad):
    res = client.get(f"{API}/jobs/{bad}", headers=auth_header(coordinator_token))
    assert res.status_code == 404 and res.json() == {"detail": "Not found."}


@pytest.mark.parametrize("bad", [0, -1, 2**31, 2**63, "abc"])
def test_an_impossible_id_in_a_body_is_a_validation_error(client, student_token, bad):
    res = client.post(f"{API}/applications", headers=auth_header(student_token), json={"job_id": bad})
    assert res.status_code == 422


def test_an_impossible_id_in_a_filter_is_a_validation_error(client, coordinator_token):
    assert client.get(f"{API}/jobs", params={"company_id": 0}, headers=auth_header(coordinator_token)).status_code == 422
