from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.database.seed import seed_reference_data
from app.models import Company, Student
from tests.conftest import STUDENT, auth_header

API = "/api/v1"
ME = f"{API}/students/me"

OTHER = {"full_name": "Ravi Kumar", "email": "ravi@example.com", "password": "Passw0rd123"}


@pytest.fixture
def seeded(db_session):
    seed_reference_data(db_session)
    return db_session


@pytest.fixture
def h(client, seeded, student_token):
    return auth_header(student_token)


@pytest.fixture
def other_h(client, seeded):
    token = client.post(f"{API}/auth/register", json=OTHER).json()["access_token"]
    return auth_header(token)


def branch_id(client, h, name="Computer Science and Engineering"):
    return next(b["id"] for b in client.get(f"{API}/branches", headers=h).json() if b["name"] == name)


def skill_id(client, h, name):
    return next(s["id"] for s in client.get(f"{API}/skills", headers=h).json() if s["name"] == name)


def valid_profile(client, h, **over):
    base = {
        "full_name": "Asha Patil", "phone": "+91 98765 43210", "college": "ABC Institute of Technology",
        "branch_id": branch_id(client, h), "year": 2, "semester": 3, "cgpa": 8.25, "backlogs": 0,
        "interests": "Web development, data", "preferred_location": "Pune", "preferred_job_type": "full_time",
    }
    return {**base, **over}


# ---------- reading ----------
def test_new_student_has_empty_profile_with_completeness_hints(client, h):
    res = client.get(ME, headers=h)
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == STUDENT["email"] and body["full_name"] == STUDENT["full_name"]
    assert body["cgpa"] is None and body["skills"] == [] and body["branch"] is None
    assert body["completeness"]["score"] == 0
    assert "CGPA" in body["completeness"]["missing"]


# ---------- create (first save) + update ----------
def test_first_save_creates_profile_and_persists(client, h, db_session):
    res = client.put(ME, headers=h, json=valid_profile(client, h))
    assert res.status_code == 200
    body = res.json()
    assert body["cgpa"] == 8.25 and body["branch"]["name"] == "Computer Science and Engineering"
    again = client.get(ME, headers=h).json()
    assert again["college"] == "ABC Institute of Technology" and again["semester"] == 3
    db_session.expire_all()
    assert float(db_session.scalar(select(Student)).cgpa) == 8.25


def test_update_overwrites_and_can_clear_optional_fields(client, h):
    client.put(ME, headers=h, json=valid_profile(client, h))
    res = client.put(ME, headers=h, json=valid_profile(client, h, cgpa=9.1, phone=None, backlogs=1))
    body = res.json()
    assert body["cgpa"] == 9.1 and body["phone"] is None and body["backlogs"] == 1


def test_whitespace_is_normalised(client, h):
    body = client.put(ME, headers=h, json=valid_profile(client, h, college="  Some   College  ")).json()
    assert body["college"] == "Some College"


def test_completeness_reaches_100(client, h):
    client.put(ME, headers=h, json=valid_profile(client, h))
    skills = [{"skill_id": skill_id(client, h, n)} for n in ("Python", "SQL", "React")]
    client.put(f"{ME}/skills", headers=h, json={"skills": skills})
    client.post(f"{ME}/projects", headers=h, json={"title": "Placement app"})
    role = client.get(f"{API}/job-roles", headers=h).json()[0]["id"]
    client.put(f"{ME}/preferences", headers=h, json={"preferred_role_ids": [role]})
    c = client.get(ME, headers=h).json()["completeness"]
    assert c["score"] == 100 and c["missing"] == []


# ---------- validation ----------
@pytest.mark.parametrize(
    "over",
    [
        {"cgpa": 10.5}, {"cgpa": -1}, {"backlogs": -1}, {"year": 0}, {"year": 7}, {"semester": 13},
        {"phone": "abc"}, {"phone": "12"}, {"full_name": "A"}, {"preferred_job_type": "weekend"},
        {"year": 2, "semester": 6},  # semester 6 belongs to year 3
    ],
)
def test_profile_validation_errors(client, h, over):
    assert client.put(ME, headers=h, json=valid_profile(client, h, **over)).status_code == 422


def test_unknown_branch_rejected(client, h):
    res = client.put(ME, headers=h, json=valid_profile(client, h, branch_id=99999))
    assert res.status_code == 422 and "branch" in res.json()["detail"].lower()


def test_cgpa_rounded_to_two_decimals(client, h):
    assert client.put(ME, headers=h, json=valid_profile(client, h, cgpa=8.256)).json()["cgpa"] == 8.26


# ---------- skills ----------
def test_skills_add_view_remove(client, h):
    py, sql = skill_id(client, h, "Python"), skill_id(client, h, "SQL")
    res = client.put(f"{ME}/skills", headers=h, json={"skills": [
        {"skill_id": py, "proficiency": "advanced"}, {"skill_id": sql}]})
    assert res.status_code == 200
    skills = {s["name"]: s for s in res.json()["skills"]}
    assert set(skills) == {"Python", "SQL"}
    assert skills["Python"]["proficiency"] == "advanced" and skills["SQL"]["proficiency"] == "beginner"
    assert skills["Python"]["source"] == "manual"

    res = client.put(f"{ME}/skills", headers=h, json={"skills": [{"skill_id": py}]})  # removes SQL
    assert [s["name"] for s in res.json()["skills"]] == ["Python"]
    assert [s["name"] for s in client.get(ME, headers=h).json()["skills"]] == ["Python"]
    assert client.put(f"{ME}/skills", headers=h, json={"skills": []}).json()["skills"] == []


def test_skill_validation(client, h):
    py = skill_id(client, h, "Python")
    assert client.put(f"{ME}/skills", headers=h, json={"skills": [{"skill_id": 99999}]}).status_code == 422
    dup = {"skills": [{"skill_id": py}, {"skill_id": py}]}
    assert client.put(f"{ME}/skills", headers=h, json=dup).status_code == 422
    bad = {"skills": [{"skill_id": py, "proficiency": "wizard"}]}
    assert client.put(f"{ME}/skills", headers=h, json=bad).status_code == 422


# ---------- certifications ----------
def test_certification_crud(client, h):
    res = client.post(f"{ME}/certifications", headers=h, json={
        "name": "AWS Cloud Practitioner", "issuer": "Amazon", "issued_on": "2025-05-01"})
    assert res.status_code == 201
    cert = res.json()["certifications"][0]
    assert cert["name"] == "AWS Cloud Practitioner" and cert["issued_on"] == "2025-05-01"

    res = client.put(f"{ME}/certifications/{cert['id']}", headers=h, json={"name": "AWS SAA"})
    assert res.json()["certifications"][0]["name"] == "AWS SAA"

    res = client.delete(f"{ME}/certifications/{cert['id']}", headers=h)
    assert res.status_code == 200 and res.json()["certifications"] == []


def test_certification_validation(client, h):
    future = (date.today() + timedelta(days=5)).isoformat()
    assert client.post(f"{ME}/certifications", headers=h, json={"name": "X"}).status_code == 422
    assert client.post(f"{ME}/certifications", headers=h, json={"name": "Valid", "issued_on": future}).status_code == 422
    assert client.post(f"{ME}/certifications", headers=h, json={}).status_code == 422


# ---------- projects ----------
def test_project_crud(client, h):
    res = client.post(f"{ME}/projects", headers=h, json={
        "title": "PlaceGenie", "description": "Placement app", "tech_stack": "React, FastAPI",
        "url": "https://github.com/x/y"})
    assert res.status_code == 201
    proj = res.json()["projects"][0]
    assert proj["tech_stack"] == "React, FastAPI"
    res = client.put(f"{ME}/projects/{proj['id']}", headers=h, json={"title": "Renamed"})
    assert res.json()["projects"][0]["title"] == "Renamed" and res.json()["projects"][0]["url"] is None
    assert client.delete(f"{ME}/projects/{proj['id']}", headers=h).json()["projects"] == []


def test_project_url_must_be_http(client, h):
    res = client.post(f"{ME}/projects", headers=h, json={"title": "Bad link", "url": "javascript:alert(1)"})
    assert res.status_code == 422


# ---------- experience ----------
def test_experience_crud_and_date_rules(client, h):
    res = client.post(f"{ME}/experiences", headers=h, json={
        "organization": "Acme", "role": "Intern", "start_date": "2025-06-01", "end_date": "2025-08-01"})
    assert res.status_code == 201
    exp = res.json()["experiences"][0]
    assert exp["role"] == "Intern"
    backwards = {"organization": "Acme", "role": "Intern", "start_date": "2025-06-01", "end_date": "2025-01-01"}
    assert client.put(f"{ME}/experiences/{exp['id']}", headers=h, json=backwards).status_code == 422
    assert client.post(f"{ME}/experiences", headers=h, json={
        "organization": "Acme", "role": "Intern", "end_date": "2025-01-01"}).status_code == 422
    assert client.delete(f"{ME}/experiences/{exp['id']}", headers=h).json()["experiences"] == []


# ---------- preferences ----------
def test_preferences(client, h, seeded):
    roles = client.get(f"{API}/job-roles", headers=h).json()
    seeded.add(Company(name="Demo Corp"))
    seeded.commit()
    company_id = seeded.scalar(select(Company.id))
    res = client.put(f"{ME}/preferences", headers=h, json={
        "preferred_role_ids": [roles[0]["id"], roles[1]["id"]], "preferred_company_ids": [company_id]})
    body = res.json()
    assert len(body["preferred_roles"]) == 2 and body["preferred_companies"][0]["name"] == "Demo Corp"
    bad = client.put(f"{ME}/preferences", headers=h, json={"preferred_role_ids": [99999]})
    assert bad.status_code == 422
    cleared = client.put(f"{ME}/preferences", headers=h, json={})
    assert cleared.json()["preferred_roles"] == []


# ---------- authorization ----------
def test_profile_requires_login(client):
    assert client.get(ME).status_code == 401
    assert client.put(ME, json={"full_name": "X Y"}).status_code == 401


def test_coordinator_cannot_use_student_profile(client, coordinator_token):
    h = auth_header(coordinator_token)
    assert client.get(ME, headers=h).status_code == 403
    assert client.put(ME, headers=h, json={"full_name": "Dr Rao"}).status_code == 403


def test_students_only_see_and_change_their_own_profile(client, h, other_h):
    client.put(ME, headers=h, json=valid_profile(client, h, college="Asha College"))
    client.put(ME, headers=other_h, json=valid_profile(client, other_h, full_name="Ravi Kumar", college="Ravi College"))
    assert client.get(ME, headers=h).json()["college"] == "Asha College"
    assert client.get(ME, headers=other_h).json()["college"] == "Ravi College"
    assert client.get(ME, headers=other_h).json()["email"] == OTHER["email"]


def test_cannot_touch_another_students_items(client, h, other_h):
    cert_id = client.post(f"{ME}/certifications", headers=h, json={"name": "Private cert"}).json()["certifications"][0]["id"]
    proj_id = client.post(f"{ME}/projects", headers=h, json={"title": "Private project"}).json()["projects"][0]["id"]
    assert client.delete(f"{ME}/certifications/{cert_id}", headers=other_h).status_code == 404
    assert client.put(f"{ME}/certifications/{cert_id}", headers=other_h, json={"name": "Hacked"}).status_code == 404
    assert client.delete(f"{ME}/projects/{proj_id}", headers=other_h).status_code == 404
    assert client.get(ME, headers=h).json()["certifications"][0]["name"] == "Private cert"
    assert client.get(ME, headers=other_h).json()["certifications"] == []


def test_profile_cannot_be_used_to_change_identity_fields(client, h, db_session):
    payload = valid_profile(client, h)
    payload.update({"email": "evil@example.com", "role": "coordinator", "user_id": 999})
    client.put(ME, headers=h, json=payload)
    body = client.get(ME, headers=h).json()
    assert body["email"] == STUDENT["email"]
    assert client.get(f"{API}/coordinators/me", headers=h).status_code == 403


# ---------- reference data ----------
def test_reference_lists_need_login_and_are_seeded(client, seeded):
    assert client.get(f"{API}/skills").status_code == 401
    token = client.post(f"{API}/auth/register", json=STUDENT).json()["access_token"]
    h = auth_header(token)
    assert len(client.get(f"{API}/branches", headers=h).json()) >= 5
    assert any(s["name"] == "Python" for s in client.get(f"{API}/skills", headers=h).json())
    assert len(client.get(f"{API}/job-roles", headers=h).json()) >= 10


def test_seed_is_idempotent(seeded):
    from app.models import Skill

    before = seeded.scalar(select(func.count()).select_from(Skill))
    assert seed_reference_data(seeded) == {"branches": 0, "skills": 0, "job_roles": 0}
    assert seeded.scalar(select(func.count()).select_from(Skill)) == before
