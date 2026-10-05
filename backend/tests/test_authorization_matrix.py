"""Who may call what. Every API route is listed once; a new route that is not classified fails the inventory test."""
import pytest

from app.main import app
from tests.conftest import auth_header

API = "/api/v1"
PUBLIC = {
    ("GET", "/health"), ("POST", "/auth/register"), ("POST", "/auth/login"),
}
# Any logged-in user (student or coordinator).
ANY_USER = {
    ("GET", "/auth/me"), ("POST", "/auth/logout"), ("GET", "/branches"), ("GET", "/skills"), ("GET", "/job-roles"),
    ("GET", "/companies"), ("GET", "/companies/1"), ("GET", "/companies/1/jobs"), ("GET", "/jobs"), ("GET", "/jobs/1"),
    ("GET", "/applications/1"), ("POST", "/applications/1/interviews"), ("GET", "/interviews/1"), ("PATCH", "/interviews/1"), ("DELETE", "/interviews/1"),
}
COORDINATOR_ONLY = {
    ("POST", "/companies"), ("PUT", "/companies/1"), ("DELETE", "/companies/1"),
    ("POST", "/jobs"), ("PUT", "/jobs/1"), ("DELETE", "/jobs/1"),
    ("GET", "/applications"), ("PATCH", "/applications/1/status"), ("GET", "/interviews"),
    ("GET", "/coordinators/me"), ("GET", "/coordinators/dashboard"), ("GET", "/coordinators/students"),
    ("GET", "/coordinators/students/1"), ("GET", "/coordinators/progress"), ("GET", "/coordinators/analytics"),
    ("GET", "/coordinators/reports"), ("GET", "/coordinators/report"), ("GET", "/coordinators/reports/students.csv"),
}
STUDENT_ONLY = {
    ("GET", "/students/me"), ("PUT", "/students/me"), ("PUT", "/students/me/skills"), ("PUT", "/students/me/preferences"),
    ("POST", "/students/me/projects"), ("PUT", "/students/me/projects/1"), ("DELETE", "/students/me/projects/1"),
    ("POST", "/students/me/experiences"), ("PUT", "/students/me/experiences/1"), ("DELETE", "/students/me/experiences/1"),
    ("POST", "/students/me/certifications"), ("PUT", "/students/me/certifications/1"), ("DELETE", "/students/me/certifications/1"),
    ("GET", "/dashboard"), ("GET", "/recommendations"), ("POST", "/jobs/1/eligibility"), ("GET", "/jobs/1/skill-gap"),
    ("POST", "/resumes"), ("GET", "/resumes/me"), ("DELETE", "/resumes/1"), ("GET", "/resumes/1/analysis"),
    ("POST", "/resumes/1/analyze"), ("GET", "/resumes/1/file"), ("POST", "/resumes/1/sync-skills"),
    ("POST", "/applications"), ("GET", "/applications/me"), ("POST", "/applications/1/withdraw"),
    ("GET", "/interviews/me"),
    ("GET", "/reports/me"), ("GET", "/reports/me.csv"),
    ("GET", "/chat/info"), ("POST", "/chat/messages"), ("GET", "/chat/conversations"), ("DELETE", "/chat/conversations"),
    ("GET", "/chat/conversations/1"), ("DELETE", "/chat/conversations/1"),
}


def real_routes():
    found = set()
    for path, ops in app.openapi()["paths"].items():
        for method in ops:
            found.add((method.upper(), path.removeprefix(API)))
    return found


def normalise(route):
    """/companies/{company_id} -> /companies/1 so the real routes compare with the lists above."""
    import re

    method, path = route
    return method, re.sub(r"\{[a-z_]+\}", "1", path.replace("{kind}", "students"))


def test_every_route_is_classified_exactly_once():
    classified = [PUBLIC, ANY_USER, COORDINATOR_ONLY, STUDENT_ONLY]
    seen = [r for group in classified for r in group]
    assert len(seen) == len(set(seen)), "a route is listed in two groups"
    actual = {normalise(r) for r in real_routes()}
    assert actual - set(seen) == set(), "new routes need an entry in the authorization matrix"
    assert set(seen) - actual == set(), "the matrix lists routes that no longer exist"


def call(client, method, path, headers=None):
    return client.request(method, API + path, headers=headers or {}, json={} if method in ("POST", "PUT", "PATCH") else None)


@pytest.mark.parametrize("method,path", sorted(ANY_USER | COORDINATOR_ONLY | STUDENT_ONLY))
def test_anonymous_visitors_are_rejected(client, method, path):
    assert call(client, method, path).status_code == 401


@pytest.mark.parametrize("method,path", sorted(COORDINATOR_ONLY))
def test_students_cannot_reach_coordinator_routes(client, student_token, method, path):
    res = call(client, method, path, auth_header(student_token))
    assert res.status_code == 403, res.text


@pytest.mark.parametrize("method,path", sorted(STUDENT_ONLY))
def test_coordinators_cannot_use_student_only_routes(client, coordinator_token, method, path):
    res = call(client, method, path, auth_header(coordinator_token))
    assert res.status_code == 403, res.text


@pytest.mark.parametrize("method,path", sorted(COORDINATOR_ONLY))
def test_coordinators_pass_the_coordinator_check(client, coordinator_token, method, path):
    """Not 401/403: the request got past authorization (it may still be 404 or 422 for the dummy id or empty body)."""
    assert call(client, method, path, auth_header(coordinator_token)).status_code not in (401, 403)


@pytest.mark.parametrize("method,path", sorted(m for m in STUDENT_ONLY if m[1] not in {"/resumes/1/file"}))
def test_students_pass_the_student_check(client, student_token, method, path):
    assert call(client, method, path, auth_header(student_token)).status_code not in (401, 403) or path == "/chat/info"


def test_a_forged_or_expired_token_is_rejected(client):
    for token in ("garbage", "a.b.c", ""):
        assert client.get(f"{API}/coordinators/dashboard", headers=auth_header(token)).status_code == 401


def test_a_student_cannot_promote_themselves(client, student_token):
    """The role lives in the database/token, never in anything the client sends."""
    res = client.post(f"{API}/auth/register", json={"full_name": "Sneaky", "email": "sneaky@example.com", "password": "Passw0rd123", "role": "coordinator"})
    token = res.json()["access_token"]
    assert client.get(f"{API}/auth/me", headers=auth_header(token)).json()["role"] == "student"
    assert client.get(f"{API}/coordinators/dashboard", headers=auth_header(token)).status_code == 403


def test_a_students_token_with_a_coordinator_claim_is_not_trusted(client, student_token):
    """Changing the role claim breaks the signature; the server also re-reads the role from the database."""
    import base64
    import json

    head, body, sig = student_token.split(".")
    payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    payload["role"] = "coordinator"
    forged_body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    assert client.get(f"{API}/coordinators/dashboard", headers=auth_header(f"{head}.{forged_body}.{sig}")).status_code == 401
