"""API tests: GET /dashboard composes the existing modules into one summary."""
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.database.seed_demo import seed_demo_data
from app.models import Company, Job, JobSkill, Skill
from app.services import dashboard_service, recommendation_service
from tests.conftest import STUDENT, auth_header
from tests.pdf_utils import FULL_RESUME, make_pdf

API = "/api/v1"
DASH = f"{API}/dashboard"
ME = f"{API}/students/me"
OTHER = {"full_name": "Ravi Kumar", "email": "ravi@example.com", "password": "Passw0rd123"}
CSE = "Computer Science and Engineering"
DATA_SKILLS = ("Python", "SQL", "Excel", "Statistics", "Pandas")


@pytest.fixture
def demo(db_session):
    seed_demo_data(db_session)
    return db_session


@pytest.fixture
def h(client, demo, student_token):
    return auth_header(student_token)


@pytest.fixture
def other_h(client, demo):
    return auth_header(client.post(f"{API}/auth/register", json=OTHER).json()["access_token"])


@pytest.fixture
def ch(client, demo, coordinator_token):
    return auth_header(coordinator_token)


def dash(client, h):
    res = client.get(DASH, headers=h)
    assert res.status_code == 200, res.text
    return res.json()


def lookup(client, h, path, name):
    return next(x["id"] for x in client.get(f"{API}/{path}", headers=h).json() if x["name"] == name)


def build_profile(client, h, skills=DATA_SKILLS, cgpa=8.2, roles=("Data Analyst",), full=True):
    client.put(ME, headers=h, json={
        "full_name": "Asha Patil", "phone": "+91 98765 43210", "college": "ABC Institute", "year": 2, "semester": 3, "cgpa": cgpa, "backlogs": 0,
        "branch_id": lookup(client, h, "branches", CSE), "interests": "data analysis and machine learning" if full else None})
    client.put(f"{ME}/skills", headers=h, json={"skills": [{"skill_id": lookup(client, h, "skills", s)} for s in skills]})
    if full:
        client.post(f"{ME}/projects", headers=h, json={"title": "Placement Predictor", "tech_stack": "Python, Pandas"})
    client.put(f"{ME}/preferences", headers=h, json={"preferred_role_ids": [lookup(client, h, "job-roles", r) for r in roles]})


def job_id(db, title):
    return db.scalar(select(Job.id).where(Job.title == title))


def apply(client, h, db, title="Data Analyst"):
    res = client.post(f"{API}/applications", headers=h, json={"job_id": job_id(db, title)})
    assert res.status_code == 201, res.text
    return res.json()


def iso(days=0, hours=0):
    return (datetime.now().replace(microsecond=0) + timedelta(days=days, hours=hours)).isoformat()


def interview(client, h, application_id, **fields):
    res = client.post(f"{API}/applications/{application_id}/interviews", headers=h, json={"stage": "technical_interview", **fields})
    assert res.status_code == 201, res.text
    return res.json()


def open_jobs(db):
    return db.scalar(select(func.count()).select_from(Job).where(Job.status == "open"))


# =====================================================================
# A brand-new student: every section works and says what to do next
# =====================================================================
def test_new_student_dashboard_has_working_empty_states(client, h, demo):
    d = dash(client, h)
    assert d["errors"] == {}
    assert d["student"]["name"] == STUDENT["full_name"] and d["student"]["first_name"] == "Asha"
    assert d["profile"]["score"] == 0 and "CGPA" in d["profile"]["missing"] and d["profile"]["skills"] == 0
    assert d["resume"] == {"uploaded": False, "filename": None, "uploaded_at": None, "completeness_score": None, "skills_detected": None, "top_suggestions": []}
    rec = d["recommendations"]
    assert rec["open_jobs"] == open_jobs(demo) and rec["eligible"] == 0 and len(rec["top"]) == 5 and len(rec["hints"]) == 5
    assert all(j["match_score"] == 0 for j in rec["top"])  # nothing to score yet
    assert d["opportunities"]["eligible_count"] == 0 and d["opportunities"]["items"] == [] and d["opportunities"]["eligible_percent"] == 0
    assert d["applications"] == {"total": 0, "active": 0, "by_status": {}, "recent": []}
    assert d["interviews"]["upcoming"] == [] and d["interviews"]["total"] == 0 and d["interviews"]["needs_result"] == 0
    assert d["skill_gaps"] == {"student_has_skills": False, "based_on_jobs": 0, "top_missing": [], "closest_job": None}
    assert d["progress"]["percent"] == 0 and d["progress"]["done"] == 0 and d["progress"]["next_step"]["key"] == "profile"
    assert d["statistics"]["in_demand_skills"] and all(s["you_have"] is False for s in d["statistics"]["in_demand_skills"])
    assert d["statistics"]["interview_pass_rate"] is None and all(f["count"] == 0 for f in d["statistics"]["application_funnel"])


def test_open_jobs_excludes_closed_and_expired_ones(client, h, demo):
    d = dash(client, h)
    # the demo data has one closed drive; none of the open jobs is past its deadline
    assert d["statistics"]["open_jobs"] == open_jobs(demo) and d["statistics"]["open_jobs"] == len(demo.scalars(select(Job).where(Job.status == "open")).all())
    job = demo.get(Job, job_id(demo, "Data Analyst"))
    job.deadline = date.today() - timedelta(days=1)
    demo.commit()
    assert dash(client, h)["statistics"]["open_jobs"] == open_jobs(demo) - 1


# =====================================================================
# An active student: the dashboard matches the individual pages
# =====================================================================
@pytest.fixture
def active(client, h, demo, ch):
    """Profile + resume + one shortlisted application with an upcoming and a passed interview."""
    build_profile(client, h)
    assert client.post(f"{API}/resumes", headers=h, files={"file": ("cv.pdf", make_pdf(FULL_RESUME), "application/pdf")}).status_code == 201
    app = apply(client, h, demo)
    client.patch(f"{API}/applications/{app['id']}/status", headers=ch, json={"status": "shortlisted"})
    upcoming = interview(client, h, app["id"], scheduled_at=iso(2), stage="technical_interview")
    interview(client, h, app["id"], scheduled_at=iso(-3), stage="online_assessment", outcome="passed")
    return {"application": app, "upcoming": upcoming}


def test_active_student_overview(client, h, active):
    d = dash(client, h)
    assert d["errors"] == {}
    assert d["profile"]["score"] == 100 and d["profile"]["missing"] == [] and d["profile"]["skills"] == 5 and d["profile"]["projects"] == 1
    assert d["resume"]["uploaded"] and d["resume"]["filename"] == "cv.pdf" and d["resume"]["completeness_score"] >= 90
    assert d["resume"]["skills_detected"] > 5 and isinstance(d["resume"]["top_suggestions"], list)
    assert d["student"]["branch"] == CSE and d["student"]["cgpa"] == 8.2
    assert d["applications"]["total"] == d["applications"]["active"] == 1 and d["applications"]["by_status"] == {"shortlisted": 1}
    recent = d["applications"]["recent"][0]
    assert recent["job_title"] == "Data Analyst" and recent["company"] == "Aurora Analytics" and recent["status"] == "shortlisted"
    assert recent["next_interview"] == active["upcoming"]["scheduled_at"]
    iv = d["interviews"]
    assert iv["upcoming_count"] == 1 and iv["upcoming"][0]["job_title"] == "Data Analyst" and iv["upcoming"][0]["stage"] == "technical_interview"
    assert (iv["total"], iv["passed"], iv["not_cleared"], iv["pending"]) == (2, 1, 0, 1)


def test_numbers_agree_with_the_other_pages(client, h, active):
    d = dash(client, h)
    recs = client.get(f"{API}/recommendations", headers=h, params={"limit": 50}).json()
    assert d["recommendations"]["open_jobs"] == recs["total"]
    assert d["recommendations"]["eligible"] == recs["counts"]["eligible"] and d["recommendations"]["not_eligible"] == recs["counts"]["not_eligible"]
    assert [(j["job_id"], j["match_score"]) for j in d["recommendations"]["top"]] == [(i["job"]["id"], i["match_score"]) for i in recs["items"][:5]]
    assert d["profile"]["score"] == client.get(ME, headers=h).json()["completeness"]["score"]
    assert d["applications"]["by_status"] == client.get(f"{API}/applications/me", headers=h).json()["counts"]
    assert d["interviews"]["upcoming_count"] == client.get(f"{API}/interviews/me", headers=h, params={"when": "upcoming"}).json()["total"]
    resume = client.get(f"{API}/resumes/me", headers=h).json()
    assert d["resume"]["completeness_score"] == client.get(f"{API}/resumes/{resume['id']}/analysis", headers=h).json()["completeness_score"]
    assert d["statistics"]["eligible_percent"] == d["opportunities"]["eligible_percent"] == round(100 * recs["counts"]["eligible"] / recs["total"])


def test_the_dashboard_updates_when_the_data_changes(client, h, active):
    before = dash(client, h)
    client.put(f"{ME}/skills", headers=h, json={"skills": [{"skill_id": lookup(client, h, "skills", "Python")}]})
    after = dash(client, h)
    assert after["profile"]["skills"] == 1 and after["recommendations"]["eligible"] < before["recommendations"]["eligible"]
    assert after["profile"]["score"] < before["profile"]["score"]  # "at least 3 skills" is no longer met
    assert "At least 3 skills" in after["profile"]["missing"]


# =====================================================================
# Recommendations, opportunities, deadlines
# =====================================================================
def test_recommendations_are_best_first_and_flag_applied_jobs(client, h, demo):
    build_profile(client, h)
    apply(client, h, demo, "Data Analyst")
    top = dash(client, h)["recommendations"]["top"]
    scores = [j["match_score"] for j in top]
    assert scores == sorted(scores, reverse=True) and len(top) == 5
    assert next(j for j in dash(client, h)["recommendations"]["top"] if j["title"] == "Data Analyst")["already_applied"] is True


def test_eligible_opportunities_exclude_jobs_already_applied_to(client, h, demo):
    build_profile(client, h)
    before = dash(client, h)["opportunities"]
    assert before["eligible_count"] >= 1 and before["items"] and all(j["eligibility"] == "ELIGIBLE" for j in before["items"])
    assert "Data Analyst" in [j["title"] for j in before["items"]]
    apply(client, h, demo, "Data Analyst")
    after = dash(client, h)["opportunities"]
    assert "Data Analyst" not in [j["title"] for j in after["items"]]
    assert after["eligible_count"] == before["eligible_count"]  # still eligible; just no longer an open opportunity


def test_closing_soon_lists_near_deadlines_you_could_still_apply_to(client, h, demo):
    build_profile(client, h)
    today = date.today()
    soon_eligible = demo.get(Job, job_id(demo, "Data Analyst"))
    soon_eligible.deadline = today + timedelta(days=2)
    soon_ineligible = demo.get(Job, job_id(demo, "Security Analyst"))  # needs skills this student lacks
    soon_ineligible.deadline = today + timedelta(days=1)
    far = demo.get(Job, job_id(demo, "Business Analyst Trainee"))
    far.deadline = today + timedelta(days=30)
    applied_job = demo.get(Job, job_id(demo, "Data Scientist"))
    applied_job.deadline = today + timedelta(days=3)
    demo.commit()
    apply(client, h, demo, "Data Scientist")
    d = dash(client, h)
    titles = [j["title"] for j in d["opportunities"]["closing_soon"]]
    assert "Data Analyst" in titles and "Security Analyst" not in titles  # ineligible job excluded
    assert "Business Analyst Trainee" not in titles and "Data Scientist" not in titles  # too far / already applied
    deadlines = [j["deadline"] for j in d["opportunities"]["closing_soon"]]
    assert deadlines == sorted(deadlines) and len(titles) <= 3
    assert d["statistics"]["closing_this_week"] >= 3  # counts every open job closing within 7 days, whoever it suits


def test_closing_soon_is_empty_when_nothing_is_due(client, h, demo):
    build_profile(client, h)
    for job in demo.scalars(select(Job)):
        job.deadline = date.today() + timedelta(days=60)
    demo.commit()
    d = dash(client, h)
    assert d["opportunities"]["closing_soon"] == [] and d["statistics"]["closing_this_week"] == 0


# =====================================================================
# Skill gaps
# =====================================================================
def test_skill_gaps_summarise_what_the_relevant_matches_need(client, h, demo):
    build_profile(client, h, skills=("Python", "SQL"))
    d = dash(client, h)["skill_gaps"]
    items = client.get(f"{API}/recommendations", headers=h, params={"limit": 50}).json()["items"]
    relevant = [i for i in items if i["match_score"] >= dashboard_service.MIN_RELEVANT_SCORE][: dashboard_service.MAX_GAP_JOBS]
    focus = relevant if len(relevant) >= dashboard_service.MIN_GAP_JOBS else items[: dashboard_service.MIN_GAP_JOBS]
    expected = {}
    for item in focus:
        for name in item["missing_skills"]:
            expected.setdefault(name, []).append(item["job"]["title"])
    assert d["student_has_skills"] is True and d["based_on_jobs"] == len(focus)
    got = {m["name"]: m["jobs_needing"] for m in d["top_missing"]}
    top6 = sorted(expected.items(), key=lambda kv: (-len(kv[1]), kv[0].lower()))[:6]
    assert got == {name: len(jobs) for name, jobs in top6}
    assert [m["jobs_needing"] for m in d["top_missing"]] == sorted((m["jobs_needing"] for m in d["top_missing"]), reverse=True)
    assert all(m["example_jobs"] for m in d["top_missing"])
    assert "Python" not in got and "SQL" not in got  # skills you have are never listed as gaps


def test_unrelated_jobs_do_not_pollute_the_skill_gaps(client, h, demo):
    build_profile(client, h)  # a data profile: several data jobs score above the relevance threshold
    d = dash(client, h)["skill_gaps"]
    items = client.get(f"{API}/recommendations", headers=h, params={"limit": 50}).json()["items"]
    assert sum(i["match_score"] >= dashboard_service.MIN_RELEVANT_SCORE for i in items) >= dashboard_service.MIN_GAP_JOBS
    names = {m["name"] for m in d["top_missing"]}
    assert not names & {"AutoCAD", "Flutter", "Kotlin", "Android Development", "Embedded C", "MATLAB"}  # civil / mobile / embedded skills
    assert d["based_on_jobs"] < len(client.get(f"{API}/recommendations", headers=h, params={"limit": 50}).json()["items"])


def test_a_thin_profile_still_gets_at_least_a_few_jobs_to_compare(client, h, demo):
    build_profile(client, h, skills=("Docker",), cgpa=5.0, full=False)
    d = dash(client, h)["skill_gaps"]
    assert d["based_on_jobs"] >= dashboard_service.MIN_GAP_JOBS and d["top_missing"]


def test_closest_job_is_one_skill_set_away(client, h, demo):
    build_profile(client, h, skills=("Python", "SQL"))  # Data Analyst also needs Excel (required)
    closest = dash(client, h)["skill_gaps"]["closest_job"]
    assert closest is not None and 1 <= len(closest["missing_skills"]) <= 3
    elig = client.post(f"{API}/jobs/{closest['job_id']}/eligibility", headers=h).json()
    assert elig["failed_requirements"] == ["Required skills"]  # skills are the only thing standing in the way
    assert sorted(elig["missing_skills"]) == sorted(closest["missing_skills"])


def test_no_closest_job_when_nothing_is_nearly_eligible(client, h, demo):
    build_profile(client, h, skills=("Docker",), cgpa=5.0)
    assert dash(client, h)["skill_gaps"]["closest_job"] is None


def test_skill_gaps_ask_for_skills_when_there_are_none(client, h, demo):
    build_profile(client, h, skills=())
    g = dash(client, h)["skill_gaps"]
    assert g["student_has_skills"] is False and g["top_missing"] == [] and g["closest_job"] is None


# =====================================================================
# Applications and interviews
# =====================================================================
def test_application_summary_by_status(client, h, demo, ch):
    a = apply(client, h, demo, "Data Analyst")
    b = apply(client, h, demo, "Security Analyst")
    apply(client, h, demo, "Android Developer")
    client.patch(f"{API}/applications/{a['id']}/status", headers=ch, json={"status": "selected"})
    client.post(f"{API}/applications/{b['id']}/withdraw", headers=h)
    apps = dash(client, h)["applications"]
    assert apps["total"] == 3 and apps["active"] == 2 and apps["by_status"] == {"selected": 1, "withdrawn": 1, "applied": 1}
    assert len(apps["recent"]) == 3 and apps["recent"][0]["job_title"] == "Android Developer"  # newest first


def test_recent_applications_are_limited_to_five(client, h, demo):
    for title in ("Data Analyst", "Security Analyst", "Android Developer", "Data Scientist", "Cloud Support Engineer", "Backend Developer (Python)"):
        apply(client, h, demo, title)
    apps = dash(client, h)["applications"]
    assert apps["total"] == 6 and len(apps["recent"]) == 5


def test_interviews_upcoming_are_soonest_first_and_limited(client, h, demo):
    app = apply(client, h, demo)
    for days in (9, 1, 5, 3, 7, 2, 4):
        interview(client, h, app["id"], scheduled_at=iso(days))
    iv = dash(client, h)["interviews"]
    times = [i["scheduled_at"] for i in iv["upcoming"]]
    assert len(times) == 5 and times == sorted(times) and iv["upcoming_count"] == 7


def test_past_interviews_needing_a_result_are_counted(client, h, demo):
    app = apply(client, h, demo)
    interview(client, h, app["id"], scheduled_at=iso(-2))  # pending result
    interview(client, h, app["id"], scheduled_at=iso(-5), outcome="failed")
    iv = dash(client, h)["interviews"]
    assert iv["needs_result"] == 1 and iv["not_cleared"] == 1 and iv["passed"] == 0 and iv["upcoming_count"] == 0


def test_withdrawn_applications_drop_out_of_upcoming_interviews(client, h, demo):
    app = apply(client, h, demo)
    interview(client, h, app["id"], scheduled_at=iso(3))
    assert dash(client, h)["interviews"]["upcoming_count"] == 1
    client.post(f"{API}/applications/{app['id']}/withdraw", headers=h)
    d = dash(client, h)
    assert d["interviews"]["upcoming_count"] == 0 and d["interviews"]["total"] == 0 and d["applications"]["active"] == 0


# =====================================================================
# Placement progress
# =====================================================================
def milestone(d, key):
    return next(m for m in d["progress"]["milestones"] if m["key"] == key)


def test_progress_follows_the_student_through_the_process(client, h, demo, ch):
    d = dash(client, h)
    assert [m["key"] for m in d["progress"]["milestones"]] == ["profile", "resume", "applied", "progressed", "interviewed", "selected"]
    assert d["progress"]["next_step"]["key"] == "profile" and d["progress"]["percent"] == 0

    build_profile(client, h)
    d = dash(client, h)
    assert milestone(d, "profile")["done"] and d["progress"]["next_step"]["key"] == "resume"

    client.post(f"{API}/resumes", headers=h, files={"file": ("cv.pdf", make_pdf(FULL_RESUME), "application/pdf")})
    d = dash(client, h)
    assert milestone(d, "resume")["done"] and d["progress"]["next_step"]["key"] == "applied"
    assert d["progress"]["next_step"]["link"] == "/student/recommendations"

    app = apply(client, h, demo)
    d = dash(client, h)
    assert milestone(d, "applied")["done"] and not milestone(d, "progressed")["done"] and d["progress"]["next_step"]["key"] == "progressed"

    client.patch(f"{API}/applications/{app['id']}/status", headers=ch, json={"status": "shortlisted"})
    d = dash(client, h)
    assert milestone(d, "progressed")["done"] and d["progress"]["next_step"]["key"] == "interviewed"

    interview(client, h, app["id"], scheduled_at=iso(2))
    d = dash(client, h)
    assert milestone(d, "interviewed")["done"] and d["progress"]["next_step"] is None  # only an offer remains, which is not an action
    assert d["progress"]["done"] == 5 and d["progress"]["percent"] == round(100 * 5 / 6)

    client.patch(f"{API}/applications/{app['id']}/status", headers=ch, json={"status": "selected"})
    d = dash(client, h)
    assert milestone(d, "selected")["done"] and d["progress"]["percent"] == 100 and d["progress"]["done"] == 6


def test_the_profile_milestone_needs_80_percent(client, h, demo):
    build_profile(client, h, full=False)  # no interests, no project
    d = dash(client, h)
    assert 0 < d["profile"]["score"] < 100
    assert milestone(d, "profile")["done"] is (d["profile"]["score"] >= 80)
    assert milestone(d, "profile")["detail"] == f"{d['profile']['score']}% complete"


def test_a_withdrawn_application_does_not_count_as_applied(client, h, demo):
    app = apply(client, h, demo)
    assert milestone(dash(client, h), "applied")["done"]
    client.post(f"{API}/applications/{app['id']}/withdraw", headers=h)
    assert not milestone(dash(client, h), "applied")["done"]


def test_every_milestone_has_a_link_to_the_page_that_fixes_it(client, h, demo):
    for m in dash(client, h)["progress"]["milestones"]:
        assert m["link"].startswith("/student/") and m["label"] and m["detail"]


# =====================================================================
# Statistics are computed, not hard-coded
# =====================================================================
def test_market_statistics_come_from_the_job_data(client, h, demo):
    build_profile(client, h)
    s = dash(client, h)["statistics"]
    live = demo.scalars(select(Job).where(Job.status == "open")).all()
    assert s["open_jobs"] == len(live) and s["companies_hiring"] == len({j.company_id for j in live})
    python = demo.scalar(select(Skill.id).where(Skill.name == "Python"))
    py_jobs = demo.scalar(select(func.count(JobSkill.job_id)).join(Job, Job.id == JobSkill.job_id).where(JobSkill.skill_id == python, Job.status == "open"))
    row = next(x for x in s["in_demand_skills"] if x["name"] == "Python")
    assert row["jobs"] == py_jobs and row["you_have"] is True
    assert [x["jobs"] for x in s["in_demand_skills"]] == sorted((x["jobs"] for x in s["in_demand_skills"]), reverse=True)
    assert len(s["in_demand_skills"]) <= 8 and any(x["you_have"] is False for x in s["in_demand_skills"])


def test_statistics_change_when_the_data_changes(client, h, demo):
    before = dash(client, h)["statistics"]
    company = demo.scalar(select(Company).where(Company.name == "Helix Secure"))
    for job in company.jobs:
        job.status = "closed"
    demo.commit()
    after = dash(client, h)["statistics"]
    assert after["open_jobs"] == before["open_jobs"] - 1 and after["companies_hiring"] == before["companies_hiring"] - 1


def test_application_funnel_and_interview_pass_rate(client, h, demo, ch):
    a = apply(client, h, demo, "Data Analyst")
    b = apply(client, h, demo, "Security Analyst")
    client.patch(f"{API}/applications/{a['id']}/status", headers=ch, json={"status": "technical_interview"})
    interview(client, h, a["id"], scheduled_at=iso(-4), outcome="passed")
    interview(client, h, a["id"], scheduled_at=iso(-3), outcome="passed")
    interview(client, h, b["id"], scheduled_at=iso(-2), outcome="failed")
    interview(client, h, b["id"], scheduled_at=iso(-1))  # no result: not part of the rate
    s = dash(client, h)["statistics"]
    funnel = {f["status"]: f["count"] for f in s["application_funnel"]}
    assert funnel["applied"] == 1 and funnel["technical_interview"] == 1 and funnel["selected"] == 0
    assert [f["status"] for f in s["application_funnel"]] == ["applied", "shortlisted", "online_assessment", "technical_interview", "hr_interview", "selected", "rejected"]
    assert s["interview_pass_rate"] == round(100 * 2 / 3)


def test_dashboard_copes_with_no_open_jobs(client, student_token):
    h = auth_header(student_token)  # nothing seeded at all
    d = dash(client, h)
    assert d["errors"] == {}
    assert d["recommendations"]["open_jobs"] == 0 and d["recommendations"]["top"] == []
    assert d["opportunities"] == {"eligible_count": 0, "eligible_percent": 0, "items": [], "closing_soon": []}
    assert d["statistics"]["open_jobs"] == 0 and d["statistics"]["in_demand_skills"] == [] and d["statistics"]["eligible_percent"] == 0
    assert d["progress"]["percent"] == 0 and d["skill_gaps"]["top_missing"] == []


# =====================================================================
# One section failing must not break the page
# =====================================================================
def test_a_failing_section_is_reported_and_the_rest_still_load(client, h, demo, monkeypatch):
    def boom(ctx):
        raise RuntimeError("secret internal detail")

    monkeypatch.setitem(dashboard_service.SECTIONS, "statistics", boom)
    res = client.get(DASH, headers=h)
    assert res.status_code == 200
    d = res.json()
    assert d["statistics"] is None and list(d["errors"]) == ["statistics"]
    assert "secret internal detail" not in res.text and "could not be loaded" in d["errors"]["statistics"]
    for ok in ("profile", "resume", "recommendations", "opportunities", "applications", "interviews", "skill_gaps", "progress"):
        assert d[ok] is not None, ok


def test_a_failure_in_shared_data_only_affects_the_sections_that_use_it(client, h, demo, monkeypatch):
    build_profile(client, h)  # with skills, the skill-gap section also depends on the scored jobs

    def boom(*args, **kwargs):
        raise RuntimeError("scoring is down")

    monkeypatch.setattr(recommendation_service, "recommend_for", boom)
    d = client.get(DASH, headers=h).json()
    assert set(d["errors"]) == {"recommendations", "opportunities", "skill_gaps", "statistics"}
    for ok in ("profile", "resume", "applications", "interviews", "progress"):
        assert d[ok] is not None, ok
    assert d["student"]["first_name"] == "Asha"


# =====================================================================
# Authorization and privacy
# =====================================================================
def test_requires_login(client, demo):
    assert client.get(DASH).status_code == 401
    assert client.get(DASH, headers=auth_header("not.a.token")).status_code == 401


def test_coordinators_do_not_have_a_student_dashboard(client, ch):
    assert client.get(DASH, headers=ch).status_code == 403


def test_each_student_sees_only_their_own_data(client, h, other_h, demo):
    build_profile(client, h)
    apply(client, h, demo)
    mine, theirs = dash(client, h), dash(client, other_h)
    assert mine["applications"]["total"] == 1 and theirs["applications"]["total"] == 0
    assert theirs["student"]["name"] == OTHER["full_name"] and theirs["profile"]["score"] == 0 and theirs["progress"]["percent"] == 0


def test_the_response_has_no_credentials_or_contact_details(client, h, active):
    text = client.get(DASH, headers=h).text.lower()
    assert "password" not in text and STUDENT["email"] not in text and "98765" not in text


def test_the_dashboard_is_read_only_and_repeatable(client, h, active, db_session):
    from sqlalchemy import text

    tables = ("students", "applications", "interview_stages", "student_skills", "resumes", "jobs")
    before = {t: db_session.execute(text(f"select count(*) from {t}")).scalar() for t in tables}
    one, two = dash(client, h), dash(client, h)
    one.pop("generated_at"), two.pop("generated_at")
    assert one == two
    assert before == {t: db_session.execute(text(f"select count(*) from {t}")).scalar() for t in tables}
