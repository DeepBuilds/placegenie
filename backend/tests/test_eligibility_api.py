"""API tests: POST /jobs/{id}/eligibility on the seeded demo jobs."""
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.database.seed_demo import seed_demo_data
from app.models import Job
from tests.conftest import STUDENT, auth_header

API = "/api/v1"
ME = f"{API}/students/me"

# "Security Analyst" at Helix Secure needs:
#   CGPA >= 7.5, no backlogs, CSE/IT/ENTC, skills Cyber Security + Computer Networks + Linux
#   (Python preferred), and the CompTIA Security+ certification.
JOB_TITLE = "Security Analyst"
CSE_NAME = "Computer Science and Engineering"


@pytest.fixture
def demo(db_session):
    seed_demo_data(db_session)
    return db_session


@pytest.fixture
def h(client, demo, student_token):
    return auth_header(student_token)


def job_id(db, title=JOB_TITLE):
    return db.scalar(select(Job.id).where(Job.title == title))


def lookup(client, h, path, name):
    return next(x["id"] for x in client.get(f"{API}/{path}", headers=h).json() if x["name"] == name)


def build_profile(client, h, *, cgpa=8.1, branch=CSE_NAME, backlogs=0,
                  skills=("Cyber Security", "Computer Networks", "Linux"), certs=("CompTIA Security+",)):
    assert client.put(ME, headers=h, json={
        "full_name": "Asha Patil", "branch_id": lookup(client, h, "branches", branch),
        "cgpa": cgpa, "backlogs": backlogs}).status_code == 200
    entries = [{"skill_id": lookup(client, h, "skills", s)} for s in skills]
    assert client.put(f"{ME}/skills", headers=h, json={"skills": entries}).status_code == 200
    for name in certs:
        assert client.post(f"{ME}/certifications", headers=h, json={"name": name}).status_code == 201


def check(client, h, jid):
    res = client.post(f"{API}/jobs/{jid}/eligibility", headers=h)
    assert res.status_code == 200, res.text
    return res.json()


def crit(body, key):
    return next(c for c in body["criteria"] if c["key"] == key)


# ---------- the required scenarios ----------
def test_eligible_student(client, h, demo):
    build_profile(client, h)
    body = check(client, h, job_id(demo))
    assert body["result"] == "ELIGIBLE" and body["eligible"] is True
    assert body["job"] == {"id": job_id(demo), "title": JOB_TITLE, "company": "Helix Secure"}
    assert all(c["status"] == "passed" for c in body["criteria"])
    assert crit(body, "cgpa")["required"] == "7.50 or above" and crit(body, "cgpa")["actual"] == "8.10"
    assert crit(body, "skills")["actual"] == "3/3 matched"
    assert body["failed_requirements"] == [] and body["missing_skills"] == []
    assert body["missing_preferred_skills"] == ["Python"]  # reported, never blocking


def test_low_cgpa(client, h, demo):
    build_profile(client, h, cgpa=6.9)
    body = check(client, h, job_id(demo))
    assert body["result"] == "NOT_ELIGIBLE" and body["eligible"] is False
    assert body["failed_requirements"] == ["CGPA"]
    c = crit(body, "cgpa")
    assert (c["status"], c["required"], c["actual"]) == ("failed", "7.50 or above", "6.90")
    assert any("6.90" in r and "7.50" in r for r in body["reasons"])


def test_wrong_branch(client, h, demo):
    build_profile(client, h, branch="Mechanical Engineering")
    body = check(client, h, job_id(demo))
    assert body["failed_requirements"] == ["Branch"]
    assert crit(body, "branch")["actual"] == "Mechanical Engineering"
    assert CSE_NAME in crit(body, "branch")["required"]


def test_too_many_backlogs(client, h, demo):
    build_profile(client, h, backlogs=1)
    body = check(client, h, job_id(demo))
    assert body["failed_requirements"] == ["Backlogs"]
    c = crit(body, "backlogs")
    assert (c["required"], c["actual"]) == ("No backlogs allowed", "1")


def test_missing_skills(client, h, demo):
    build_profile(client, h, skills=("Cyber Security", "Python"))
    body = check(client, h, job_id(demo))
    assert body["failed_requirements"] == ["Required skills"]
    assert body["missing_skills"] == ["Computer Networks", "Linux"]
    assert crit(body, "skills")["actual"] == "1/3 matched"
    assert body["missing_preferred_skills"] == []  # Python is held


def test_missing_certification(client, h, demo):
    build_profile(client, h, certs=())
    body = check(client, h, job_id(demo))
    assert body["failed_requirements"] == ["Certifications"]
    assert body["missing_certifications"] == ["CompTIA Security+"]


def test_multiple_failures(client, h, demo):
    build_profile(client, h, cgpa=6.0, branch="Civil Engineering", backlogs=3, skills=("Python",), certs=())
    body = check(client, h, job_id(demo))
    assert body["result"] == "NOT_ELIGIBLE"
    assert body["failed_requirements"] == ["CGPA", "Branch", "Backlogs", "Required skills", "Certifications"]
    assert len(body["reasons"]) == 5
    assert body["missing_skills"] == ["Computer Networks", "Cyber Security", "Linux"]
    assert "5 requirements" in body["summary"]


# ---------- other behaviour ----------
def test_experience_requirement_from_profile(client, h, demo):
    jid = job_id(demo, "Backend Developer (Python)")  # CSE/IT, CGPA 8, 6 months experience
    build_profile(client, h, cgpa=8.5, skills=("Python", "FastAPI", "PostgreSQL", "REST APIs"), certs=())
    assert crit(check(client, h, jid), "experience")["status"] == "failed"
    start = (date.today() - timedelta(days=240)).isoformat()
    client.post(f"{ME}/experiences", headers=h, json={"organization": "Acme", "role": "Intern", "start_date": start})
    body = check(client, h, jid)
    assert crit(body, "experience")["status"] == "passed" and crit(body, "experience")["actual"] == "8 months"  # 240 days
    assert body["result"] == "ELIGIBLE"


def test_job_open_to_all_branches_and_fresher_friendly(client, h, demo):
    build_profile(client, h, cgpa=6.6, branch="Civil Engineering", backlogs=1, skills=("Excel", "SQL", "Communication"), certs=())
    body = check(client, h, job_id(demo, "Business Analyst Trainee"))  # CGPA 6.5, 2 backlogs, all branches
    assert body["result"] == "ELIGIBLE"
    assert crit(body, "branch")["required"] == "All branches"


def test_result_updates_when_profile_changes(client, h, demo):
    build_profile(client, h, cgpa=6.9)
    assert check(client, h, job_id(demo))["eligible"] is False
    client.put(ME, headers=h, json={"full_name": "Asha Patil", "branch_id": lookup(client, h, "branches", CSE_NAME), "cgpa": 8.0, "backlogs": 0})
    assert check(client, h, job_id(demo))["eligible"] is True


def test_new_student_with_empty_profile_gets_failures_not_a_crash(client, h, demo):
    body = check(client, h, job_id(demo))  # no CGPA, no branch, no skills
    assert body["eligible"] is False and body["result"] == "NOT_ELIGIBLE"  # skills + certs genuinely fail
    assert body["incomplete_fields"] == ["CGPA", "Branch"]
    assert crit(body, "cgpa")["status"] == "not_evaluated"


def test_incomplete_profile_result_when_nothing_else_fails(client, h, demo):
    body = check(client, h, job_id(demo, "Business Analyst Trainee"))  # no CGPA entered yet
    skills_needed = body["missing_skills"]
    assert skills_needed  # student has no skills, so this job still fails on skills
    for s in ("Excel", "SQL", "Communication"):
        client.put(f"{ME}/skills", headers=h, json={"skills": [{"skill_id": lookup(client, h, "skills", n)} for n in ("Excel", "SQL", "Communication")]})
    body = check(client, h, job_id(demo, "Business Analyst Trainee"))
    assert body["result"] == "INCOMPLETE_PROFILE" and body["eligible"] is False
    assert body["incomplete_fields"] == ["CGPA"] and body["failed_requirements"] == []


def test_expired_deadline_blocks_eligibility(client, h, demo):
    build_profile(client, h)
    job = demo.get(Job, job_id(demo))
    job.deadline = date.today() - timedelta(days=1)
    demo.commit()
    body = check(client, h, job.id)
    assert body["result"] == "NOT_ELIGIBLE" and body["failed_requirements"] == ["Application window"]


def test_nothing_is_stored_by_a_check(client, h, demo):
    from sqlalchemy import text

    build_profile(client, h)
    before = {t: demo.execute(text(f"select count(*) from {t}")).scalar() for t in ("students", "applications", "student_skills")}
    check(client, h, job_id(demo))
    after = {t: demo.execute(text(f"select count(*) from {t}")).scalar() for t in before}
    assert before == after


# ---------- errors and authorization ----------
def test_unknown_job_404(client, h):
    assert client.post(f"{API}/jobs/99999/eligibility", headers=h).status_code == 404


def test_closed_job_hidden_from_students(client, h, demo):
    closed = demo.scalar(select(Job).where(Job.status == "closed"))
    assert client.post(f"{API}/jobs/{closed.id}/eligibility", headers=h).status_code == 404


def test_requires_login(client, demo):
    assert client.post(f"{API}/jobs/{job_id(demo)}/eligibility").status_code == 401


def test_coordinators_cannot_use_student_eligibility(client, demo, coordinator_token):
    res = client.post(f"{API}/jobs/{job_id(demo)}/eligibility", headers=auth_header(coordinator_token))
    assert res.status_code == 403


def test_each_student_is_checked_against_their_own_profile(client, h, demo):
    build_profile(client, h)  # eligible student
    other = client.post(f"{API}/auth/register", json={"full_name": "Ravi", "email": "ravi@example.com", "password": "Passw0rd123"}).json()
    other_h = auth_header(other["access_token"])
    assert check(client, h, job_id(demo))["eligible"] is True
    assert check(client, other_h, job_id(demo))["eligible"] is False
