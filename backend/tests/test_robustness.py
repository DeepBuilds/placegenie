"""Malformed input must never crash the API: every route is called with odd ids, bodies and parameters
as a visitor, a student and a coordinator, and must answer with a 4xx (or 2xx), never a 5xx."""
import re

import pytest

from app.database.seed_demo import seed_demo_data
from app.main import app
from tests.conftest import auth_header

API = "/api/v1"
ODD_IDS = ["0", "-1", "9223372036854775808", "99999", "abc", "1.5", "%00"]
ODD_BODIES = [None, {}, [], "text", 12, {"x": None}, {"name": "", "title": "", "email": "a"}, {"skills": "nope"},
              {"name": "x" * 10_000, "full_name": "\u0000‮", "status": "hired", "job_id": "1; DROP TABLE users"},
              {"job_id": 2**63, "skill_id": -5, "cgpa": "NaN", "year": 10**30}]
ODD_QUERIES = [{"limit": "-1"}, {"limit": "100000"}, {"offset": "-5"}, {"q": "%' OR 1=1 --"}, {"q": "x" * 5000},
               {"status": "nope"}, {"company_id": "abc"}, {"min_cgpa": "NaN"}, {"sort": "random"}, {"when": "yesterday"}]


def routes():
    out = []
    for path, ops in app.openapi()["paths"].items():
        for method in ops:
            out.append((method.upper(), path.removeprefix(API)))
    return sorted(out)


def fill(path, value):
    return re.sub(r"\{[a-z_]+\}", value, path.replace("{kind}.csv", f"{value}.csv"))


@pytest.fixture
def headers(client, db_session, student_token, coordinator_token):
    seed_demo_data(db_session)
    return {"visitor": {}, "student": auth_header(student_token), "coordinator": auth_header(coordinator_token)}


def send(client, method, path, h, body=None, params=None, raw=None):
    if raw is not None:
        return client.request(method, API + path, headers={**h, "Content-Type": "application/json"}, content=raw, params=params)
    if body is None:
        return client.request(method, API + path, headers=h, params=params)
    return client.request(method, API + path, headers=h, json=body, params=params)


@pytest.mark.parametrize("method,path", routes())
def test_no_route_crashes_on_odd_input(client, headers, method, path):
    failures = []
    for who, h in headers.items():
        ids = ODD_IDS if "{" in path else [None]
        for odd in ids:
            p = fill(path, odd) if odd is not None else path
            for body in (ODD_BODIES if method in ("POST", "PUT", "PATCH") else [None]):
                res = send(client, method, p, h, body=body)
                if res.status_code >= 500:
                    failures.append((who, p, body, res.status_code, res.text[:200]))
            if method in ("POST", "PUT", "PATCH"):
                for raw in (b"{not json", b"\xff\xfe", b"[" * 5000, b'{"a":' * 2000):
                    res = send(client, method, p, h, raw=raw)
                    if res.status_code >= 500:
                        failures.append((who, p, raw[:20], res.status_code, res.text[:200]))
        if method == "GET" and "{" not in path:
            for q in ODD_QUERIES:
                res = send(client, method, path, h, params=q)
                if res.status_code >= 500:
                    failures.append((who, path, q, res.status_code, res.text[:200]))
    assert not failures, "\n".join(map(str, failures[:10]))
