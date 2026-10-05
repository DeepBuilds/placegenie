from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.database.seed_demo import COMPANIES, JOBS, seed_demo_data
from app.models import Application, Company, Job, JobSkill, Role, Skill, Student, User
from tests.conftest import auth_header

API = "/api/v1"
OPEN_JOBS = sum(1 for j in JOBS if j[9].value == "open")


@pytest.fixture
def demo(db_session):
    seed_demo_data(db_session)
    return db_session


@pytest.fixture
def sh(client, demo, student_token):  # student headers
    return auth_header(student_token)


@pytest.fixture
def ch(client, demo, coordinator_token):  # coordinator headers
    return auth_header(coordinator_token)


def ids(db, model, name):
    return db.scalar(select(model.id).where(model.name == name))


def titles(res):
    return [j["title"] for j in res.json()["items"]]


def job_payload(db, **over):
    base = {
        "company_id": db.scalar(select(Company.id).limit(1)),
        "title": "Test Engineer",
        "description": "Testing things",
        "location": "Pune",
        "job_type": "full_time",
        "min_cgpa": 7.0,
        "max_backlogs": 1,
        "min_experience_months": 0,
        "deadline": (date.today() + timedelta(days=20)).isoformat(),
        "status": "open",
        "skills": [{"skill_id": ids(db, Skill, "Python"), "importance": "required", "weight": 3}],
        "allowed_branch_ids": [],
        "required_certifications": [],
    }
    return {**base, **over}


# ---------- demo data ----------
def test_demo_data_meets_requirements(demo):
    assert demo.scalar(select(func.count()).select_from(Company)) >= 8
    assert demo.scalar(select(func.count()).select_from(Job)) >= 15
    assert demo.scalar(select(func.count()).select_from(Skill)) >= 20
    jobs = demo.scalars(select(Job)).all()
    assert len({float(j.min_cgpa) for j in jobs}) >= 4  # varied CGPA requirements
    assert len({j.max_backlogs for j in jobs}) >= 3  # varied backlog limits
    assert any(not j.allowed_branches for j in jobs) and any(j.allowed_branches for j in jobs)
    assert len({j.role_id for j in jobs}) >= 8
    assert any(j.required_certifications for j in jobs)
    assert any(j.min_experience_months > 0 for j in jobs)


def test_demo_seed_is_idempotent(demo):
    jobs_before = demo.scalar(select(func.count()).select_from(Job))
    assert seed_demo_data(demo) == {"companies_added": 0, "jobs_added": 0}
    assert demo.scalar(select(func.count()).select_from(Job)) == jobs_before
    assert jobs_before == len(JOBS) and demo.scalar(select(func.count()).select_from(Company)) == len(COMPANIES)


# ---------- authentication ----------
def test_all_read_endpoints_need_login(client, demo):
    for path in ("/jobs", "/jobs/1", "/companies", "/companies/1", "/companies/1/jobs"):
        assert client.get(API + path).status_code == 401, path


# ---------- student visibility ----------
def test_student_sees_only_open_jobs(client, sh):
    res = client.get(f"{API}/jobs?limit=100", headers=sh)
    assert res.status_code == 200
    assert res.json()["total"] == OPEN_JOBS
    assert all(j["status"] == "open" for j in res.json()["items"])
    assert "Frontend Developer (Closed Drive)" not in titles(res)


def test_student_cannot_widen_visibility_with_status_param(client, sh):
    res = client.get(f"{API}/jobs?status=closed&limit=100", headers=sh)
    assert res.json()["total"] == OPEN_JOBS


def test_student_cannot_open_closed_job_by_id(client, sh, demo):
    closed = demo.scalar(select(Job).where(Job.status == "closed"))
    assert client.get(f"{API}/jobs/{closed.id}", headers=sh).status_code == 404


def test_coordinator_sees_all_and_can_filter_by_status(client, ch):
    assert client.get(f"{API}/jobs?limit=100", headers=ch).json()["total"] == len(JOBS)
    res = client.get(f"{API}/jobs?status=closed", headers=ch)
    assert titles(res) == ["Frontend Developer (Closed Drive)"]


# ---------- job detail ----------
def test_get_job_returns_full_requirements(client, sh, demo):
    job = demo.scalar(select(Job).where(Job.title == "Security Analyst"))
    body = client.get(f"{API}/jobs/{job.id}", headers=sh).json()
    assert body["company"]["name"] == "Helix Secure"
    assert body["role"]["name"] == "Cyber Security Analyst"
    assert body["min_cgpa"] == 7.5 and body["max_backlogs"] == 0
    assert body["required_certifications"] == ["CompTIA Security+"]
    assert {b["name"] for b in body["allowed_branches"]} == {
        "Computer Science and Engineering", "Information Technology",
        "Electronics and Telecommunication Engineering"}
    assert body["skills"][0]["importance"] == "required"
    assert {"Cyber Security", "Linux", "Python"} <= {s["name"] for s in body["skills"]}
    assert body["is_expired"] is False


def test_get_missing_job_404(client, sh):
    assert client.get(f"{API}/jobs/99999", headers=sh).status_code == 404


# ---------- search and filters ----------
def test_search_by_title_company_skill_and_description(client, sh):
    assert "Android Developer" in titles(client.get(f"{API}/jobs?q=android", headers=sh))
    helix = client.get(f"{API}/jobs?q=helix", headers=sh)
    assert titles(helix) == ["Security Analyst"]
    by_skill = titles(client.get(f"{API}/jobs?q=power bi&limit=100", headers=sh))
    assert by_skill == ["Data Analyst"]
    assert "Cloud Support Engineer" in titles(client.get(f"{API}/jobs?q=troubleshoot", headers=sh))


def test_search_treats_wildcards_literally(client, sh):
    assert client.get(f"{API}/jobs?q=%25", headers=sh).json()["total"] == 0
    assert client.get(f"{API}/jobs?q=_", headers=sh).json()["total"] == 0


def test_filter_by_company_and_company_jobs_endpoint(client, sh, demo):
    cid = ids(demo, Company, "Aurora Analytics")
    a = client.get(f"{API}/jobs?company_id={cid}", headers=sh)
    b = client.get(f"{API}/companies/{cid}/jobs", headers=sh)
    assert a.json()["total"] == b.json()["total"] == 3
    assert titles(a) == titles(b)


def test_filter_job_type_role_skill_location(client, sh, demo):
    internships = client.get(f"{API}/jobs?job_type=internship", headers=sh)
    assert sorted(titles(internships)) == ["DevOps Engineer Intern", "Flutter Developer Intern"]

    from app.models import JobRole

    role = ids(demo, JobRole, "Data Analyst")
    assert titles(client.get(f"{API}/jobs?role_id={role}", headers=sh)) == ["Data Analyst"]

    docker = ids(demo, Skill, "Docker")
    got = set(titles(client.get(f"{API}/jobs?skill_id={docker}&limit=100", headers=sh)))
    assert got == {"DevOps Engineer Intern", "Cloud Support Engineer", "Backend Developer (Python)"}

    remote = client.get(f"{API}/jobs?location=remote", headers=sh)
    assert set(titles(remote)) == {"Android Developer", "Flutter Developer Intern"}


def test_filter_by_branch_includes_open_to_all_jobs(client, sh, demo):
    from app.models import Branch

    civil = ids(demo, Branch, "Civil Engineering")
    got = set(titles(client.get(f"{API}/jobs?branch_id={civil}&limit=100", headers=sh)))
    assert "Site Engineer Trainee" in got  # civil-only job
    assert "Business Analyst Trainee" in got  # open to every branch
    assert "Full Stack Developer" not in got  # CSE/IT/AIDS only
    assert "Graduate Engineer Trainee (Mechanical)" not in got


def test_filter_max_min_cgpa(client, sh):
    res = client.get(f"{API}/jobs?max_min_cgpa=6.5&limit=100", headers=sh)
    assert res.json()["total"] > 0
    assert all(j["min_cgpa"] <= 6.5 for j in res.json()["items"])
    assert client.get(f"{API}/jobs?max_min_cgpa=11", headers=sh).status_code == 422


def test_combined_filters(client, sh, demo):
    from app.models import Branch

    cse = ids(demo, Branch, "Computer Science and Engineering")
    res = client.get(f"{API}/jobs?branch_id={cse}&max_min_cgpa=7&job_type=full_time&limit=100", headers=sh)
    assert res.status_code == 200
    assert all(j["min_cgpa"] <= 7 and j["job_type"] == "full_time" for j in res.json()["items"])


def test_hide_expired(client, ch, demo):
    job = demo.scalar(select(Job).where(Job.title == "Data Analyst"))
    job.deadline = date.today() - timedelta(days=1)
    demo.commit()
    all_jobs = client.get(f"{API}/jobs?q=Data Analyst", headers=ch).json()["items"]
    expired = next(j for j in all_jobs if j["id"] == job.id)
    assert expired["is_expired"] is True
    hidden = client.get(f"{API}/jobs?hide_expired=true&limit=100", headers=ch).json()["items"]
    assert job.id not in {j["id"] for j in hidden}


def test_sorting_and_pagination(client, sh):
    by_cgpa = [j["min_cgpa"] for j in client.get(f"{API}/jobs?sort=cgpa_low&limit=100", headers=sh).json()["items"]]
    assert by_cgpa == sorted(by_cgpa)
    by_title = titles(client.get(f"{API}/jobs?sort=title&limit=100", headers=sh))
    assert by_title == sorted(by_title)
    page1 = client.get(f"{API}/jobs?limit=5&offset=0&sort=title", headers=sh).json()
    page2 = client.get(f"{API}/jobs?limit=5&offset=5&sort=title", headers=sh).json()
    assert page1["total"] == OPEN_JOBS and len(page1["items"]) == 5
    assert not {j["id"] for j in page1["items"]} & {j["id"] for j in page2["items"]}
    assert client.get(f"{API}/jobs?sort=hack", headers=sh).status_code == 422
    assert client.get(f"{API}/jobs?limit=1000", headers=sh).status_code == 422


# ---------- companies (read) ----------
def test_company_list_search_and_detail(client, sh, demo):
    res = client.get(f"{API}/companies", headers=sh)
    assert res.json()["total"] == len(COMPANIES)
    aurora = next(c for c in res.json()["items"] if c["name"] == "Aurora Analytics")
    assert aurora["open_jobs"] == 3
    assert [c["name"] for c in client.get(f"{API}/companies?q=cyber", headers=sh).json()["items"]] == ["Helix Secure"]
    one = client.get(f"{API}/companies/{aurora['id']}", headers=sh).json()
    assert one["industry"] == "Data & Analytics" and one["open_jobs"] == 3
    assert client.get(f"{API}/companies/99999", headers=sh).status_code == 404
    assert client.get(f"{API}/companies/99999/jobs", headers=sh).status_code == 404


def test_open_job_count_ignores_closed_jobs(client, sh, demo):
    zenith = client.get(f"{API}/companies/{ids(demo, Company, 'Zenith Software Labs')}", headers=sh).json()
    assert zenith["open_jobs"] == 2  # 3 jobs, 1 closed


# ---------- authorization of writes ----------
def test_students_cannot_manage_companies_or_jobs(client, sh, demo):
    company = {"name": "Evil Corp"}
    assert client.post(f"{API}/companies", headers=sh, json=company).status_code == 403
    assert client.put(f"{API}/companies/1", headers=sh, json=company).status_code == 403
    assert client.delete(f"{API}/companies/1", headers=sh).status_code == 403
    payload = job_payload(demo)
    assert client.post(f"{API}/jobs", headers=sh, json=payload).status_code == 403
    assert client.put(f"{API}/jobs/1", headers=sh, json=payload).status_code == 403
    assert client.delete(f"{API}/jobs/1", headers=sh).status_code == 403
    assert demo.scalar(select(func.count()).select_from(Company)) == len(COMPANIES)


def test_anonymous_cannot_write(client, demo):
    assert client.post(f"{API}/companies", json={"name": "Nope Inc"}).status_code == 401
    assert client.delete(f"{API}/jobs/1").status_code == 401


# ---------- company CRUD ----------
def test_company_crud(client, ch):
    res = client.post(f"{API}/companies", headers=ch, json={
        "name": "  Fresh   Startup ", "industry": "AI", "website": "https://fresh.example.com", "location": "Goa"})
    assert res.status_code == 201
    company = res.json()
    assert company["name"] == "Fresh Startup" and company["open_jobs"] == 0

    res = client.put(f"{API}/companies/{company['id']}", headers=ch, json={"name": "Fresh Startup Ltd", "industry": "ML"})
    assert res.status_code == 200 and res.json()["name"] == "Fresh Startup Ltd" and res.json()["website"] is None

    assert client.delete(f"{API}/companies/{company['id']}", headers=ch).status_code == 204
    assert client.get(f"{API}/companies/{company['id']}", headers=ch).status_code == 404
    assert client.delete(f"{API}/companies/{company['id']}", headers=ch).status_code == 404


def test_company_validation_and_duplicates(client, ch):
    assert client.post(f"{API}/companies", headers=ch, json={"name": "A"}).status_code == 422
    assert client.post(f"{API}/companies", headers=ch, json={"name": "Okay Co", "website": "ftp://x"}).status_code == 422
    assert client.post(f"{API}/companies", headers=ch, json={"name": "nimbus cloudworks"}).status_code == 409
    other = client.post(f"{API}/companies", headers=ch, json={"name": "Other Co"}).json()
    assert client.put(f"{API}/companies/{other['id']}", headers=ch, json={"name": "Helix Secure"}).status_code == 409
    assert client.put(f"{API}/companies/{other['id']}", headers=ch, json={"name": "Other Co"}).status_code == 200


def test_deleting_company_removes_its_jobs(client, ch, demo):
    cid = ids(demo, Company, "Helix Secure")
    assert client.delete(f"{API}/companies/{cid}", headers=ch).status_code == 204
    assert demo.scalar(select(func.count()).select_from(Job).where(Job.company_id == cid)) == 0
    assert demo.scalar(select(func.count()).select_from(JobSkill).where(JobSkill.job_id.notin_(select(Job.id)))) == 0


# ---------- job CRUD ----------
def test_job_create_get_update_delete(client, ch, sh, demo):
    from app.models import Branch

    cse = ids(demo, Branch, "Computer Science and Engineering")
    sql = ids(demo, Skill, "SQL")
    payload = job_payload(demo, title="  Platform   Engineer ", allowed_branch_ids=[cse],
                          required_certifications=["AWS CP", "aws cp", "Azure Fundamentals"],
                          skills=[{"skill_id": ids(demo, Skill, "Python"), "importance": "required", "weight": 3},
                                  {"skill_id": sql, "importance": "preferred", "weight": 1}])
    res = client.post(f"{API}/jobs", headers=ch, json=payload)
    assert res.status_code == 201, res.text
    job = res.json()
    assert job["title"] == "Platform Engineer"
    assert job["required_certifications"] == ["AWS CP", "Azure Fundamentals"]  # case-insensitive dedupe
    assert [s["name"] for s in job["skills"]] == ["Python", "SQL"]
    assert [b["name"] for b in job["allowed_branches"]] == ["Computer Science and Engineering"]
    assert client.get(f"{API}/jobs/{job['id']}", headers=sh).status_code == 200  # visible to students

    update = job_payload(demo, title="Platform Engineer II", min_cgpa=8, max_backlogs=None,
                         skills=[{"skill_id": sql, "importance": "required", "weight": 2}],
                         allowed_branch_ids=[], required_certifications=[], status="closed")
    res = client.put(f"{API}/jobs/{job['id']}", headers=ch, json=update)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["title"] == "Platform Engineer II" and body["min_cgpa"] == 8 and body["max_backlogs"] is None
    assert [s["name"] for s in body["skills"]] == ["SQL"] and body["allowed_branches"] == []
    assert body["required_certifications"] == [] and body["status"] == "closed"
    assert client.get(f"{API}/jobs/{job['id']}", headers=sh).status_code == 404  # closed -> hidden from students

    assert client.delete(f"{API}/jobs/{job['id']}", headers=ch).status_code == 204
    assert client.get(f"{API}/jobs/{job['id']}", headers=ch).status_code == 404
    assert client.put(f"{API}/jobs/{job['id']}", headers=ch, json=update).status_code == 404
    assert client.delete(f"{API}/jobs/{job['id']}", headers=ch).status_code == 404


def test_update_job_can_keep_same_skills(client, ch, demo):
    """Replacing children with identical keys must not trip the composite primary keys."""
    job = demo.scalar(select(Job).where(Job.title == "Security Analyst"))
    current = client.get(f"{API}/jobs/{job.id}", headers=ch).json()
    payload = job_payload(
        demo, company_id=current["company"]["id"], title=current["title"],
        skills=[{"skill_id": s["skill_id"], "importance": s["importance"], "weight": s["weight"]} for s in current["skills"]],
        allowed_branch_ids=[b["id"] for b in current["allowed_branches"]],
        required_certifications=current["required_certifications"])
    assert client.put(f"{API}/jobs/{job.id}", headers=ch, json=payload).status_code == 200


@pytest.mark.parametrize(
    "over",
    [
        {"company_id": 99999}, {"role_id": 99999}, {"title": "A"}, {"min_cgpa": 11}, {"min_cgpa": -1},
        {"max_backlogs": -1}, {"min_experience_months": -5}, {"job_type": "weekend"}, {"status": "weird"},
        {"skills": [{"skill_id": 99999}]}, {"allowed_branch_ids": [99999]},
        {"deadline": (date.today() - timedelta(days=1)).isoformat()},
        {"deadline": "not-a-date"},
    ],
)
def test_job_validation_errors(client, ch, demo, over):
    assert client.post(f"{API}/jobs", headers=ch, json=job_payload(demo, **over)).status_code == 422


def test_job_duplicate_skill_or_branch_rejected(client, ch, demo):
    py = ids(demo, Skill, "Python")
    dup_skill = job_payload(demo, skills=[{"skill_id": py}, {"skill_id": py}])
    assert client.post(f"{API}/jobs", headers=ch, json=dup_skill).status_code == 422
    from app.models import Branch

    b = ids(demo, Branch, "Civil Engineering")
    assert client.post(f"{API}/jobs", headers=ch, json=job_payload(demo, allowed_branch_ids=[b, b])).status_code == 422


def test_missing_required_fields_rejected(client, ch):
    assert client.post(f"{API}/jobs", headers=ch, json={"title": "No company"}).status_code == 422


# ---------- deletion guards ----------
def _apply(db, job_id):
    user = User(email="applicant@example.com", password_hash="x", role=Role.STUDENT)
    user.student = Student(full_name="Applicant")
    db.add(user)
    db.flush()
    db.add(Application(student_id=user.student.id, job_id=job_id))
    db.commit()


def test_job_with_applications_cannot_be_deleted(client, ch, demo):
    job = demo.scalar(select(Job).where(Job.title == "Android Developer"))
    _apply(demo, job.id)
    res = client.delete(f"{API}/jobs/{job.id}", headers=ch)
    assert res.status_code == 409 and "closed" in res.json()["detail"]
    assert demo.get(Job, job.id) is not None


def test_company_with_applications_cannot_be_deleted(client, ch, demo):
    job = demo.scalar(select(Job).where(Job.title == "Android Developer"))
    _apply(demo, job.id)
    assert client.delete(f"{API}/companies/{job.company_id}", headers=ch).status_code == 409
    assert demo.get(Company, job.company_id) is not None
