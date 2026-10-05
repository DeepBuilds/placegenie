"""API tests: GET /jobs/{id}/skill-gap on the seeded demo jobs."""
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select, text

from app.database.seed_demo import seed_demo_data
from app.models import Company, Job, JobSkill, Skill
from tests.conftest import auth_header

API = "/api/v1"
ME = f"{API}/students/me"

# Security Analyst at Helix Secure: required Cyber Security (w3), Computer Networks (w3), Linux (w2);
# preferred Python (w1).
SECURITY = "Security Analyst"
SECURITY_REQUIRED = ["Computer Networks", "Cyber Security", "Linux"]


@pytest.fixture
def demo(db_session):
    seed_demo_data(db_session)
    return db_session


@pytest.fixture
def h(client, demo, student_token):
    return auth_header(student_token)


def job_id(db, title=SECURITY):
    return db.scalar(select(Job.id).where(Job.title == title))


def set_skills(client, h, names):
    ids = {s["name"]: s["id"] for s in client.get(f"{API}/skills", headers=h).json()}
    res = client.put(f"{ME}/skills", headers=h, json={"skills": [{"skill_id": ids[n]} for n in names]})
    assert res.status_code == 200


def gap(client, h, jid):
    res = client.get(f"{API}/jobs/{jid}/skill-gap", headers=h)
    assert res.status_code == 200, res.text
    return res.json()


def names(items):
    return [i["name"] for i in items]


# ---------- the required scenarios ----------
def test_complete_match(client, h, demo):
    set_skills(client, h, [*SECURITY_REQUIRED, "Python"])
    body = gap(client, h, job_id(demo))
    assert body["job"] == {"id": job_id(demo), "title": SECURITY, "company": "Helix Secure"}
    assert body["match_percentage"] == 100 and body["required_match_percentage"] == 100
    assert sorted(names(body["matched_skills"])) == sorted([*SECURITY_REQUIRED, "Python"])
    assert body["missing_skills"] == [] and body["priority"] == []
    assert body["matched_count"] == 4 and body["missing_count"] == 0 and body["total_count"] == 4
    assert body["summary"] == "You have all 4 skills this job asks for."


def test_partial_match(client, h, demo):
    set_skills(client, h, ["Cyber Security", "Python"])
    body = gap(client, h, job_id(demo))
    assert names(body["matched_skills"]) == ["Cyber Security", "Python"]
    assert sorted(names(body["missing_skills"])) == ["Computer Networks", "Linux"]
    assert body["required_matched"] == 1 and body["required_total"] == 3 and body["required_match_percentage"] == 33
    assert body["match_percentage"] == round(100 * 1.5 / 3.5)  # (1 required + 0.5 preferred) of (3 + 0.5)
    assert {m["required"] for m in body["matched_skills"]} == {True, False}
    assert body["student_has_skills"] is True and body["notes"] == []


def test_zero_match(client, h, demo):
    set_skills(client, h, ["Excel", "Tableau"])  # real skills, none of them wanted here
    body = gap(client, h, job_id(demo))
    assert body["match_percentage"] == 0 and body["required_match_percentage"] == 0
    assert body["matched_skills"] == [] and body["missing_count"] == 4
    assert body["student_has_skills"] is True


def test_empty_student_skills(client, h, demo):
    body = gap(client, h, job_id(demo))  # a brand-new student has no skills
    assert body["match_percentage"] == 0 and body["matched_skills"] == [] and body["missing_count"] == 4
    assert body["student_has_skills"] is False
    assert any("no skills yet" in n for n in body["notes"])
    assert len(body["priority"]) == 4


def test_job_with_no_skills(client, h, demo):
    job = Job(company_id=demo.scalar(select(Company.id)), title="Open Application", status="open")
    demo.add(job)
    demo.commit()
    set_skills(client, h, ["Python"])
    body = gap(client, h, job.id)
    assert body["has_requirements"] is False and body["match_percentage"] is None
    assert body["required_match_percentage"] is None and body["total_count"] == 0
    assert body["matched_skills"] == [] and body["missing_skills"] == [] and body["priority"] == []
    assert "nothing to compare" in body["summary"]


def test_job_with_only_preferred_skills(client, h, demo):
    job = Job(company_id=demo.scalar(select(Company.id)), title="Flexible Role", status="open")
    rare = demo.scalar(select(Skill.id).where(Skill.name == "Flutter"))  # asked for by a single demo job
    demo.add(job)
    demo.flush()
    demo.add(JobSkill(job_id=job.id, skill_id=rare, importance="preferred", weight=1))
    demo.commit()
    body = gap(client, h, job.id)
    assert body["required_total"] == 0 and body["required_match_percentage"] is None
    assert body["match_percentage"] == 0 and body["missing_skills"][0]["priority"] == "low"


# ---------- priority on real data ----------
def test_missing_skills_are_prioritised_with_reasons(client, h, demo):
    body = gap(client, h, job_id(demo))
    levels = {m["name"]: m["priority"] for m in body["missing_skills"]}
    assert levels["Cyber Security"] == "high" and levels["Computer Networks"] == "high"  # weight 3 = essential
    assert levels["Linux"] in ("medium", "high")  # weight 2: medium unless asked for by >= 30% of open jobs
    assert levels["Python"] in ("low", "medium")
    assert [p["rank"] for p in body["priority"]] == [1, 2, 3, 4]
    assert body["priority"][0]["level"] == "high" and body["priority"][-1]["name"] == "Python"
    cyber = next(m for m in body["missing_skills"] if m["name"] == "Cyber Security")
    assert cyber["essential"] is True and cyber["weight"] == 3
    assert "Required for this job" in cyber["reasons"] and any("Essential" in r for r in cyber["reasons"])
    order = [m["priority"] for m in body["missing_skills"]]
    assert order == sorted(order, key={"high": 0, "medium": 1, "low": 2}.get)


def test_demand_figures_match_the_database(client, h, demo):
    body = gap(client, h, job_id(demo))
    python = next(m for m in body["missing_skills"] if m["name"] == "Python")
    expected = demo.scalar(
        select(func.count(JobSkill.job_id)).join(Job, Job.id == JobSkill.job_id)
        .where(JobSkill.skill_id == python["skill_id"], Job.status == "open")
    )
    assert python["jobs_requiring"] == expected > 3
    assert body["open_jobs_compared"] == demo.scalar(select(func.count()).select_from(Job).where(Job.status == "open"))
    assert abs(python["demand_share"] - expected / body["open_jobs_compared"]) < 0.001
    assert any(f"Asked for in {expected} of {body['open_jobs_compared']} open jobs" in r for r in python["reasons"])


def test_frequently_requested_required_skill_becomes_high_priority(client, h, demo):
    # SQL is required by several demo jobs; at BrightPath's "Associate Software Engineer" it has weight 2.
    body = gap(client, h, job_id(demo, "Associate Software Engineer"))
    sql = next(m for m in body["missing_skills"] if m["name"] == "SQL")
    assert sql["weight"] == 2 and sql["essential"] is False
    assert sql["demand_share"] >= 0.30 and sql["priority"] == "high"
    assert any("frequently requested" in r for r in sql["reasons"])


def test_closed_jobs_do_not_count_towards_demand(client, h, demo):
    closed = demo.scalar(select(Job).where(Job.status == "closed"))  # a closed drive asking for React/JavaScript/HTML/CSS
    before = gap(client, h, job_id(demo, "Full Stack Developer"))
    react = next(m for m in before["missing_skills"] if m["name"] == "React")
    assert react["jobs_requiring"] == 1  # only the open Full Stack role, not the closed drive
    assert closed is not None


# ---------- consistency with the rest of the app ----------
def test_percentage_equals_the_recommenders_skill_score(client, h, demo):
    set_skills(client, h, ["Python", "SQL", "Statistics", "Excel"])
    items = client.get(f"{API}/recommendations", headers=h, params={"limit": 50}).json()["items"]
    for item in items:
        skills = next(c for c in item["breakdown"] if c["key"] == "skills")
        if not skills["available"]:
            continue
        assert gap(client, h, item["job"]["id"])["match_percentage"] == round(skills["score"] * 100), item["job"]["title"]


def test_missing_skills_agree_with_the_eligibility_check(client, h, demo):
    set_skills(client, h, ["Cyber Security"])
    jid = job_id(demo)
    body = gap(client, h, jid)
    elig = client.post(f"{API}/jobs/{jid}/eligibility", headers=h).json()
    required_missing = sorted(m["name"] for m in body["missing_skills"] if m["required"])
    assert required_missing == elig["missing_skills"]
    optional_missing = sorted(m["name"] for m in body["missing_skills"] if not m["required"])
    assert optional_missing == elig["missing_preferred_skills"]


def test_matched_skills_show_the_students_level(client, h, demo):
    ids = {s["name"]: s["id"] for s in client.get(f"{API}/skills", headers=h).json()}
    client.put(f"{ME}/skills", headers=h, json={"skills": [{"skill_id": ids["Linux"], "proficiency": "advanced"}]})
    linux = gap(client, h, job_id(demo))["matched_skills"][0]
    assert linux["name"] == "Linux" and linux["student_level"] == "advanced"


def test_result_changes_when_the_profile_changes(client, h, demo):
    jid = job_id(demo)
    assert gap(client, h, jid)["match_percentage"] == 0
    set_skills(client, h, SECURITY_REQUIRED)
    assert gap(client, h, jid)["match_percentage"] == round(100 * 3 / 3.5)


def test_disclaimer_and_no_learning_claims(client, h, demo):
    body = gap(client, h, job_id(demo))
    assert "do not predict hiring decisions" in body["disclaimer"]
    blob = " ".join([body["summary"], *body["notes"], *(r for m in body["missing_skills"] for r in m["reasons"])]).lower()
    assert not any(w in blob for w in ("weeks", "months", "hours", "course", "tutorial", "guarantee"))


def test_deterministic_and_stores_nothing(client, h, demo):
    set_skills(client, h, ["Python"])
    jid = job_id(demo)
    before = {t: demo.execute(text(f"select count(*) from {t}")).scalar() for t in ("students", "student_skills", "applications", "jobs")}
    assert gap(client, h, jid) == gap(client, h, jid)
    assert before == {t: demo.execute(text(f"select count(*) from {t}")).scalar() for t in before}


# ---------- errors and authorization ----------
def test_unknown_job_404(client, h):
    assert client.get(f"{API}/jobs/99999/skill-gap", headers=h).status_code == 404
    assert client.get(f"{API}/jobs/abc/skill-gap", headers=h).status_code == 422


def test_closed_job_hidden_from_students(client, h, demo):
    closed = demo.scalar(select(Job).where(Job.status == "closed"))
    assert client.get(f"{API}/jobs/{closed.id}/skill-gap", headers=h).status_code == 404


def test_expired_but_open_job_can_still_be_analysed(client, h, demo):
    job = demo.get(Job, job_id(demo))
    job.deadline = date.today() - timedelta(days=2)
    demo.commit()
    assert gap(client, h, job.id)["total_count"] == 4


def test_requires_login(client, demo):
    assert client.get(f"{API}/jobs/{job_id(demo)}/skill-gap").status_code == 401


def test_coordinators_cannot_use_student_skill_gap(client, demo, coordinator_token):
    res = client.get(f"{API}/jobs/{job_id(demo)}/skill-gap", headers=auth_header(coordinator_token))
    assert res.status_code == 403


def test_each_student_sees_only_their_own_comparison(client, h, demo):
    set_skills(client, h, SECURITY_REQUIRED)
    other = client.post(f"{API}/auth/register", json={"full_name": "Ravi", "email": "r@example.com", "password": "Passw0rd123"}).json()
    assert gap(client, h, job_id(demo))["match_percentage"] > 0
    assert gap(client, auth_header(other["access_token"]), job_id(demo))["match_percentage"] == 0
