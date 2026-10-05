"""API tests: the coordinator dashboard, students, progress, analytics and reports."""
import csv
import io
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.security import create_access_token, hash_password
from app.database.seed_demo import seed_demo_data
from app.models import (
    Application,
    ApplicationStatus,
    Branch,
    InterviewStage,
    InterviewStageType,
    Job,
    Project,
    Resume,
    Role,
    Skill,
    StageOutcome,
    Student,
    StudentSkill,
    User,
)
from app.services import coordinator_service, dashboard_service
from tests.conftest import auth_header

API = "/api/v1"
CO = f"{API}/coordinators"


def token_for(user):
    return auth_header(create_access_token(user.id, user.role.value))


def make_student(db, name, branch=None, cgpa=None, *, year=None, college="ABC Institute", skills=(), resume=False, project=False, backlogs=0):
    slug = name.lower().replace(" ", ".")
    user = User(email=f"{slug}@example.com", password_hash=hash_password("Passw0rd123"), role=Role.STUDENT)
    student = Student(
        full_name=name, college=college, cgpa=cgpa, year=year, semester=(2 * year - 1) if year else None, backlogs=backlogs,
        branch_id=db.scalar(select(Branch.id).where(Branch.name == branch)) if branch else None,
    )
    user.student = student
    db.add(user)
    db.flush()
    for skill in skills:
        db.add(StudentSkill(student_id=student.id, skill_id=db.scalar(select(Skill.id).where(Skill.name == skill))))
    if project:
        db.add(Project(student_id=student.id, title="A project"))
    if resume:
        db.add(Resume(student_id=student.id, file_path="resumes/x.pdf", original_name="cv.pdf", mime_type="application/pdf", size_bytes=10, extracted_text="text", is_active=True))
    db.commit()
    return student


def job(db, title):
    return db.scalar(select(Job).where(Job.title == title))


def apply(db, student, title, status="applied"):
    app = Application(student_id=student.id, job_id=job(db, title).id, status=ApplicationStatus(status))
    db.add(app)
    db.commit()
    return app


def add_interview(db, app, days, outcome="pending", stage="technical_interview"):
    when = (datetime.now() + timedelta(days=days)).replace(microsecond=0)
    db.add(InterviewStage(application_id=app.id, stage=InterviewStageType(stage), scheduled_at=when, outcome=StageOutcome(outcome)))
    db.commit()


CSE, IT, MECH, CIVIL = "Computer Science and Engineering", "Information Technology", "Mechanical Engineering", "Civil Engineering"
DATA = ("Python", "SQL", "Excel", "Statistics", "Pandas")


@pytest.fixture
def demo(db_session):
    seed_demo_data(db_session)
    return db_session


@pytest.fixture
def ch(client, demo, coordinator_token):
    return auth_header(coordinator_token)


@pytest.fixture
def cohort(demo):
    """Seven students at different points of the process (see the expected numbers in the tests)."""
    db = demo
    s = {}
    s["asha"] = make_student(db, "Asha Patil", CSE, 8.5, year=2, skills=DATA, resume=True, project=True)
    s["bhavna"] = make_student(db, "Bhavna Rao", CSE, 7.8, year=3, skills=("Python", "SQL"), resume=True)
    s["chirag"] = make_student(db, "Chirag Shah", IT, 6.5, year=2, college="XYZ College")
    s["dev"] = make_student(db, "Dev Kumar", MECH, 7.0, year=4, skills=("AutoCAD",))
    s["esha"] = make_student(db, "Esha Nair", CIVIL, 9.1, year=3)
    s["farah"] = make_student(db, "Farah Khan", CSE, None, year=2)
    s["gopal"] = make_student(db, "Gopal Iyer", IT, 5.2, year=2, backlogs=2)
    a = apply(db, s["asha"], "Data Analyst", "selected")
    apply(db, s["bhavna"], "Data Scientist", "shortlisted")
    apply(db, s["bhavna"], "Security Analyst", "applied")
    apply(db, s["chirag"], "Associate Software Engineer", "rejected")
    d = apply(db, s["dev"], "Graduate Engineer Trainee (Mechanical)", "technical_interview")
    apply(db, s["esha"], "Site Engineer Trainee", "withdrawn")
    apply(db, s["gopal"], "Android Developer", "applied")
    add_interview(db, a, -5, "passed")
    add_interview(db, d, -2, "failed")
    add_interview(db, d, 3, "pending", "hr_interview")
    return s


def get(client, ch, path, **params):
    res = client.get(f"{CO}{path}", headers=ch, params=params)
    assert res.status_code == 200, res.text
    return res.json()


# =====================================================================
# Dashboard
# =====================================================================
def test_dashboard_statistics(client, ch, cohort, demo):
    stats = get(client, ch, "/dashboard")["stats"]
    assert stats["total_students"] == 7 and stats["total_companies"] == 10 and stats["total_jobs"] == 19 and stats["open_jobs"] == 18
    assert stats["total_applications"] == 7 and stats["withdrawn_applications"] == 1
    assert stats["applicants"] == 5  # Esha only has a withdrawn application, Farah none
    assert stats["shortlisted_students"] == 2  # Bhavna (shortlisted) and Dev (technical interview)
    assert stats["selected_students"] == 1 and stats["rejected_applications"] == 1
    assert stats["placement_rate"] == {"percent": 14, "placed": 1, "total_students": 7, "sufficient_data": True, "note": "1 of 7 registered students have a selected application."}


def test_stats_agree_with_the_database(client, ch, cohort, demo):
    stats = get(client, ch, "/dashboard")["stats"]
    assert stats["total_applications"] == demo.scalar(select(func.count()).select_from(Application))
    assert stats["total_students"] == demo.scalar(select(func.count()).select_from(Student))
    assert stats["total_jobs"] == demo.scalar(select(func.count()).select_from(Job))


def test_a_placement_rate_needs_enough_students(client, ch, demo):
    for name in ("Student One", "Student Two", "Student Three"):
        make_student(demo, name, CSE, 8.0)
    apply(demo, demo.scalar(select(Student)), "Data Analyst", "selected")
    rate = get(client, ch, "/dashboard")["stats"]["placement_rate"]
    assert rate["percent"] is None and rate["sufficient_data"] is False and rate["placed"] == 1 and rate["total_students"] == 3
    assert "at least 5" in rate["note"]
    for name in ("Student Four", "Student Five"):
        make_student(demo, name, CSE, 8.0)
    rate = get(client, ch, "/dashboard")["stats"]["placement_rate"]
    assert rate["percent"] == 20 and rate["sufficient_data"] is True  # 1 of 5


def test_dashboard_with_no_students_or_applications(client, ch, demo):
    d = get(client, ch, "/dashboard")
    assert d["stats"]["total_students"] == 0 and d["stats"]["total_applications"] == 0 and d["stats"]["placement_rate"]["percent"] is None
    assert d["recent_applications"] == [] and all(f["count"] == 0 for f in d["application_funnel"])
    assert d["attention"]["awaiting_review"] == 0 and d["attention"]["open_jobs_without_applications"] == 18


def test_dashboard_on_an_empty_platform(client, coordinator_token):
    d = get(client, auth_header(coordinator_token), "/dashboard")
    assert d["stats"]["total_students"] == 0 and d["stats"]["total_jobs"] == 0 and d["stats"]["placement_rate"]["percent"] is None
    assert d["attention"]["closing_soon"] == []


def test_application_funnel_and_recent_applications(client, ch, cohort):
    d = get(client, ch, "/dashboard")
    funnel = {f["status"]: f["count"] for f in d["application_funnel"]}
    assert funnel == {"applied": 2, "shortlisted": 1, "online_assessment": 0, "technical_interview": 1, "hr_interview": 0, "selected": 1, "rejected": 1, "withdrawn": 1}
    assert [f["status"] for f in d["application_funnel"]][:3] == ["applied", "shortlisted", "online_assessment"]
    recent = d["recent_applications"]
    assert len(recent) == 5 and recent[0]["student_name"] == "Gopal Iyer" and recent[0]["job_title"] == "Android Developer"
    assert [r["id"] for r in recent] == sorted((r["id"] for r in recent), reverse=True)
    assert {"id", "student_id", "student_name", "job_title", "company", "status", "applied_at"} <= set(recent[0])


def test_attention_items(client, ch, cohort, demo):
    soon = demo.get(Job, job(demo, "Data Analyst").id)
    soon.deadline = date.today() + timedelta(days=2)
    demo.get(Job, job(demo, "Android Developer").id).deadline = date.today() + timedelta(days=1)
    demo.get(Job, job(demo, "QA Engineer").id if job(demo, "QA Engineer") else job(demo, "Quality Assurance Engineer").id).deadline = date.today() + timedelta(days=40)
    demo.commit()
    a = get(client, ch, "/dashboard")["attention"]
    assert a["awaiting_review"] == 2  # Bhavna's Security Analyst and Gopal's Android Developer
    assert [j["title"] for j in a["closing_soon"]] == ["Android Developer", "Data Analyst"]  # soonest first
    assert [j["applications"] for j in a["closing_soon"]] == [1, 1]
    assert a["interviews_this_week"] == 1 and a["open_jobs_without_applications"] == 18 - 6  # six open jobs have a live (not withdrawn) application


# =====================================================================
# Students
# =====================================================================
def names(page):
    return [r["full_name"] for r in page["items"]]


def test_student_list_shows_every_student_with_placement_stage(client, ch, cohort):
    page = get(client, ch, "/students", limit=50)
    assert page["total"] == 7 and names(page) == sorted(names(page), key=str.lower)
    by = {r["full_name"]: r for r in page["items"]}
    assert by["Asha Patil"]["stage"] == "placed" and by["Bhavna Rao"]["stage"] == "in_process" and by["Dev Kumar"]["stage"] == "in_process"
    assert by["Chirag Shah"]["stage"] == "rejected" and by["Gopal Iyer"]["stage"] == "applied"
    assert by["Esha Nair"]["stage"] == "not_applied" and by["Farah Khan"]["stage"] == "not_applied"  # a withdrawn application does not count
    assert by["Bhavna Rao"]["applications"] == 2 and by["Esha Nair"]["applications"] == 0
    assert by["Asha Patil"]["has_resume"] is True and by["Chirag Shah"]["has_resume"] is False
    assert by["Asha Patil"]["email"] == "asha.patil@example.com" and by["Asha Patil"]["branch"]["name"] == CSE and by["Asha Patil"]["cgpa"] == 8.5
    assert page["stage_counts"] == {"placed": 1, "in_process": 2, "applied": 1, "rejected": 1, "not_applied": 2}


def test_profile_percent_matches_the_students_own_page(client, ch, cohort):
    row = next(r for r in get(client, ch, "/students", limit=50)["items"] if r["full_name"] == "Asha Patil")
    own = client.get(f"{API}/students/me", headers=token_for(cohort["asha"].user)).json()["completeness"]["score"]
    assert row["profile_percent"] == own and 0 < own < 100


@pytest.mark.parametrize("query,expected", [
    ({"q": "asha"}, ["Asha Patil"]), ({"q": "PATIL"}, ["Asha Patil"]), ({"q": "dev.kumar@"}, ["Dev Kumar"]),
    ({"q": "xyz college"}, ["Chirag Shah"]), ({"q": "nobody"}, []), ({"q": "%"}, []), ({"q": "_"}, []),
    ({"branch_id": "CSE"}, ["Asha Patil", "Bhavna Rao", "Farah Khan"]), ({"year": 2}, ["Asha Patil", "Chirag Shah", "Farah Khan", "Gopal Iyer"]),
    ({"min_cgpa": 8}, ["Asha Patil", "Esha Nair"]), ({"min_cgpa": 9.5}, []),
    ({"stage": "in_process"}, ["Bhavna Rao", "Dev Kumar"]), ({"stage": "not_applied"}, ["Esha Nair", "Farah Khan"]), ({"stage": "placed"}, ["Asha Patil"]),
    ({"has_resume": "true"}, ["Asha Patil", "Bhavna Rao"]), ({"has_resume": "false"}, ["Chirag Shah", "Dev Kumar", "Esha Nair", "Farah Khan", "Gopal Iyer"]),
    ({"q": "a", "stage": "in_process", "branch_id": "CSE"}, ["Bhavna Rao"]),
])
def test_student_search_and_filters(client, ch, cohort, demo, query, expected):
    if query.get("branch_id") == "CSE":
        query = {**query, "branch_id": demo.scalar(select(Branch.id).where(Branch.name == CSE))}
    assert names(get(client, ch, "/students", limit=50, **query)) == expected


def test_profile_ready_filter(client, ch, cohort):
    ready = get(client, ch, "/students", limit=50, profile_ready="true")
    not_ready = get(client, ch, "/students", limit=50, profile_ready="false")
    assert ready["total"] + not_ready["total"] == 7
    assert all(r["profile_percent"] >= dashboard_service.PROFILE_READY_PERCENT for r in ready["items"])
    assert all(r["profile_percent"] < dashboard_service.PROFILE_READY_PERCENT for r in not_ready["items"])


def test_stage_counts_ignore_the_stage_filter(client, ch, cohort):
    page = get(client, ch, "/students", stage="placed")
    assert page["total"] == 1 and page["stage_counts"]["in_process"] == 2 and sum(page["stage_counts"].values()) == 7


def test_student_sorting(client, ch, cohort):
    cgpa = get(client, ch, "/students", limit=50, sort="cgpa")["items"]
    assert [r["cgpa"] for r in cgpa][:6] == [9.1, 8.5, 7.8, 7.0, 6.5, 5.2] and cgpa[-1]["cgpa"] is None  # students without a CGPA last
    apps = get(client, ch, "/students", limit=50, sort="applications")["items"]
    assert apps[0]["full_name"] == "Bhavna Rao"
    profile = [r["profile_percent"] for r in get(client, ch, "/students", limit=50, sort="profile")["items"]]
    assert profile == sorted(profile, reverse=True)
    assert get(client, ch, "/students", limit=50, sort="newest")["items"][0]["full_name"] == "Gopal Iyer"


def test_student_pagination(client, ch, cohort):
    p1, p2, p3 = (get(client, ch, "/students", limit=3, offset=o) for o in (0, 3, 6))
    assert p1["total"] == 7 and len(p1["items"]) == len(p2["items"]) == 3 and len(p3["items"]) == 1
    assert names(p1) + names(p2) + names(p3) == names(get(client, ch, "/students", limit=50))


@pytest.mark.parametrize("params", [{"stage": "hired"}, {"limit": 0}, {"limit": 101}, {"offset": -1}, {"sort": "random"}, {"year": 9}, {"min_cgpa": 11}])
def test_student_list_validation(client, ch, params):
    assert client.get(f"{CO}/students", headers=ch, params=params).status_code == 422


# =====================================================================
# One student's placement profile
# =====================================================================
def test_student_detail_matches_the_students_own_pages(client, ch, cohort):
    s = cohort["bhavna"]
    detail = get(client, ch, f"/students/{s.id}")
    own = token_for(s.user)
    assert detail["student_id"] == s.id and detail["stage"] == "in_process" and detail["errors"] == {}
    assert detail["profile"]["full_name"] == "Bhavna Rao" and detail["profile"]["email"] == "bhavna.rao@example.com" and detail["profile"]["cgpa"] == 7.8
    assert {x["name"] for x in detail["profile"]["skills"]} == {"Python", "SQL"}
    assert detail["profile"]["completeness"] == client.get(f"{API}/students/me", headers=own).json()["completeness"]
    assert detail["applications"] == client.get(f"{API}/applications/me", headers=own).json()
    assert detail["interviews"] == client.get(f"{API}/interviews/me", headers=own).json()
    student_dash = client.get(f"{API}/dashboard", headers=own).json()
    assert detail["progress"] == student_dash["progress"] and detail["resume"] == student_dash["resume"] and detail["skill_gaps"] == student_dash["skill_gaps"]


def test_student_detail_shows_applications_resume_and_interviews(client, ch, cohort):
    dev = get(client, ch, f"/students/{cohort['dev'].id}")
    assert dev["stage"] == "in_process" and dev["resume"]["uploaded"] is False
    assert [a["status"] for a in dev["applications"]["items"]] == ["technical_interview"]
    assert dev["interviews"]["total"] == 2 and dev["interviews"]["counts"]["upcoming"] == 1
    asha = get(client, ch, f"/students/{cohort['asha'].id}")
    assert asha["stage"] == "placed" and asha["resume"]["uploaded"] is True and asha["progress"]["milestones"][5]["done"] is True


def test_student_detail_for_a_student_who_has_done_nothing(client, ch, cohort):
    d = get(client, ch, f"/students/{cohort['farah'].id}")
    assert d["stage"] == "not_applied" and d["applications"]["items"] == [] and d["progress"]["done"] == 0
    assert d["progress"]["next_step"]["key"] == "profile"


def test_student_detail_unknown_id(client, ch, cohort):
    assert client.get(f"{CO}/students/99999", headers=ch).status_code == 404
    assert client.get(f"{CO}/students/abc", headers=ch).status_code == 422


def test_looking_at_a_student_changes_nothing(client, ch, cohort, demo):
    from sqlalchemy import text

    before = {t: demo.execute(text(f"select count(*) from {t}")).scalar() for t in ("students", "applications", "interview_stages", "student_skills", "resumes")}
    get(client, ch, f"/students/{cohort['asha'].id}")
    get(client, ch, "/students", limit=50)
    assert before == {t: demo.execute(text(f"select count(*) from {t}")).scalar() for t in before}


# =====================================================================
# Cohort progress
# =====================================================================
def test_cohort_progress_funnel(client, ch, cohort):
    p = get(client, ch, "/progress")
    funnel = {s["key"]: s["count"] for s in p["funnel"]}
    assert p["total_students"] == 7 and funnel["registered"] == 7
    assert funnel["resume"] == 2 and funnel["applied"] == 5 and funnel["progressed"] == 3 and funnel["interviewed"] == 2 and funnel["selected"] == 1
    assert [s["key"] for s in p["funnel"]] == ["registered", "profile", "resume", "applied", "progressed", "interviewed", "selected"]
    assert p["funnel"][3]["percent"] == round(100 * 5 / 7)
    assert {s["key"]: s["count"] for s in p["current_stage"]} == {"placed": 1, "in_process": 2, "applied": 1, "rejected": 1, "not_applied": 2}
    assert p["needs_attention"]["no_resume"] == 5 and p["needs_attention"]["not_applied"] == 2


def test_cohort_progress_equals_the_sum_of_every_students_own_tracker(client, ch, cohort, demo):
    """The cohort numbers must be the students' own milestones added up - not a second, different definition."""
    done = {}
    for s in demo.scalars(select(Student)):
        for m in dashboard_service.build_dashboard(demo, s.user, only={"progress"}).progress.milestones:
            done[m.key] = done.get(m.key, 0) + m.done
    funnel = {s["key"]: s["count"] for s in get(client, ch, "/progress")["funnel"]}
    for key in ("profile", "resume", "applied", "progressed", "interviewed", "selected"):
        assert funnel[key] == done[key], key


def test_progress_with_no_students(client, ch, demo):
    p = get(client, ch, "/progress")
    assert p["total_students"] == 0 and all(s["count"] == 0 and s["percent"] == 0 for s in p["funnel"])


# =====================================================================
# Analytics
# =====================================================================
def test_analytics_by_company(client, ch, cohort):
    rows = {r["company"]: r for r in get(client, ch, "/analytics")["by_company"]}
    aurora = rows["Aurora Analytics"]  # Data Analyst (selected) + Data Scientist is QuantaRetail
    assert (aurora["applications"], aurora["selected"], aurora["shortlisted"], aurora["jobs"]) == (1, 1, 0, 3)
    assert rows["QuantaRetail Tech"]["shortlisted"] == 1 and rows["BrightPath Infotech"]["rejected"] == 1
    assert rows["Meridian Core Industries"]["shortlisted"] == 1  # Dev, technical interview
    top = get(client, ch, "/analytics")["by_company"]
    assert [r["applications"] for r in top] == sorted((r["applications"] for r in top), reverse=True) and len(top) <= 10


def test_analytics_by_branch_hides_rates_for_small_groups(client, ch, cohort):
    a = get(client, ch, "/analytics")
    cse = next(b for b in a["by_branch"] if b["branch"] == CSE)
    assert (cse["students"], cse["applicants"], cse["placed"]) == (3, 2, 1) and cse["placement_rate"] is None  # only 3 students
    assert a["min_group_size"] == 5


def test_analytics_branch_rate_appears_with_enough_students(client, ch, cohort, demo):
    for name in ("Cse One", "Cse Two"):
        make_student(demo, name, CSE, 8.0)
    cse = next(b for b in get(client, ch, "/analytics")["by_branch"] if b["branch"] == CSE)
    assert cse["students"] == 5 and cse["placed"] == 1 and cse["placement_rate"] == 20


def test_analytics_by_cgpa_band(client, ch, cohort):
    bands = {b["band"]: b for b in get(client, ch, "/analytics")["by_cgpa"]}
    assert bands["Below 6.0"]["students"] == 1 and bands["6.0 - 6.9"]["students"] == 1 and bands["7.0 - 7.9"]["students"] == 2
    assert bands["8.0 - 8.9"]["students"] == 1 and bands["9.0 and above"]["students"] == 1 and bands["CGPA not entered"]["students"] == 1
    assert sum(b["students"] for b in bands.values()) == 7 and bands["8.0 - 8.9"]["placed"] == 1


def test_skill_supply_compares_demand_with_students(client, ch, cohort, demo):
    rows = {r["skill"]: r for r in get(client, ch, "/analytics")["skill_supply"]}
    python = demo.scalar(select(Skill.id).where(Skill.name == "Python"))
    from app.repositories import job_repository

    demand, _ = job_repository.skill_demand(demo)
    assert rows["Python"]["jobs_requiring"] == demand[python] and rows["Python"]["students_with"] == 2  # Asha and Bhavna
    assert rows["Python"]["students_percent"] == round(100 * 2 / 7)
    ordered = get(client, ch, "/analytics")["skill_supply"]
    assert [r["jobs_requiring"] for r in ordered] == sorted((r["jobs_requiring"] for r in ordered), reverse=True) and len(ordered) <= 12


def test_analytics_interview_outcomes_and_status_funnel(client, ch, cohort):
    a = get(client, ch, "/analytics")
    assert a["interview_outcomes"] == {"total": 3, "passed": 1, "not_cleared": 1, "pending": 1, "pass_rate": 50}
    assert {f["status"]: f["count"] for f in a["status_funnel"]}["withdrawn"] == 1


def test_analytics_with_no_data(client, ch, demo):
    a = get(client, ch, "/analytics")
    assert a["by_branch"] == [] and a["by_cgpa"] == [] and a["interview_outcomes"]["pass_rate"] is None
    assert all(r["students_percent"] == 0 for r in a["skill_supply"])


# =====================================================================
# Reports (CSV)
# =====================================================================
def rows_of(res):
    assert res.text.startswith("﻿")
    return list(csv.reader(io.StringIO(res.text.lstrip("﻿"))))


def report(client, ch, kind):
    res = client.get(f"{CO}/reports/{kind}.csv", headers=ch)
    assert res.status_code == 200, res.text
    return res


def test_reports_are_listed(client, ch):
    listed = client.get(f"{CO}/reports", headers=ch).json()
    assert [r["kind"] for r in listed] == ["students", "applications", "placements", "companies", "skills"]
    assert all(r["url"].endswith(".csv") and r["description"] for r in listed)


def test_students_report(client, ch, cohort):
    res = report(client, ch, "students")
    assert res.headers["content-type"].startswith("text/csv") and res.headers["cache-control"] == "no-store"
    assert res.headers["content-disposition"] == f'attachment; filename="placegenie-students-{date.today().isoformat()}.csv"'
    rows = rows_of(res)
    assert rows[0][:3] == ["Student ID", "Name", "Email"] and len(rows) == 8
    asha = next(r for r in rows if r[1] == "Asha Patil")
    assert asha[2] == "asha.patil@example.com" and asha[4] == CSE and asha[7] == "8.5" and asha[10] == "Yes" and asha[12] == "Placed"


def test_applications_report(client, ch, cohort):
    rows = rows_of(report(client, ch, "applications"))
    assert len(rows) == 8 and rows[0][0] == "Application ID"
    selected = next(r for r in rows if r[1] == "Asha Patil")
    assert selected[4:7] == ["Aurora Analytics", "Data Analyst", "selected"]
    assert sum(r[6] == "technical interview" for r in rows) == 1  # statuses are written for people, not as codes


def test_placements_report_only_lists_selected_students(client, ch, cohort):
    rows = rows_of(report(client, ch, "placements"))
    assert len(rows) == 2 and rows[1][1] == "Asha Patil" and rows[1][5:7] == ["Aurora Analytics", "Data Analyst"]


def test_companies_and_skills_reports(client, ch, cohort):
    companies = rows_of(report(client, ch, "companies"))
    assert companies[0][0] == "Company" and len(companies) == 11
    aurora = next(r for r in companies if r[0] == "Aurora Analytics")
    assert aurora[1:] == ["3", "3", "1", "0", "1", "0"]  # jobs, open jobs, applications, shortlisted, selected, rejected
    skills = rows_of(report(client, ch, "skills"))
    assert skills[0] == ["Skill", "Open jobs requiring it", "Students who have it", "% of students"] and len(skills) > 10


def test_reports_match_the_screens(client, ch, cohort):
    assert len(rows_of(report(client, ch, "students"))) - 1 == get(client, ch, "/students", limit=1)["total"]
    assert len(rows_of(report(client, ch, "applications"))) - 1 == get(client, ch, "/dashboard")["stats"]["total_applications"]


def test_reports_cannot_be_used_to_run_spreadsheet_formulas(client, ch, demo):
    make_student(demo, "=HYPERLINK(\"http://evil.example\",\"click\")", CSE, 8.0)
    make_student(demo, "+cmd|' /C calc'!A0", CSE, 8.0)
    rows = rows_of(report(client, ch, "students"))
    cells = {r[1] for r in rows[1:]}
    assert "'=HYPERLINK(\"http://evil.example\",\"click\")" in cells and "'+cmd|' /C calc'!A0" in cells
    assert not any(c.startswith(("=", "+", "-", "@")) for r in rows[1:] for c in r)


def test_special_characters_survive_csv_quoting(client, ch, demo):
    make_student(demo, 'Ann "The Ace", Jr.', CSE, 8.0, college="Line1\nLine2")
    row = next(r for r in rows_of(report(client, ch, "students")) if r[1].startswith("Ann"))
    assert row[1] == 'Ann "The Ace", Jr.' and row[3] == "Line1\nLine2"


def test_unknown_report(client, ch):
    res = client.get(f"{CO}/reports/secrets.csv", headers=ch)
    assert res.status_code == 404 and "Unknown report" in res.json()["detail"]


def test_empty_reports_still_have_headers(client, ch, demo):
    for kind in ("students", "applications", "placements"):
        assert len(rows_of(report(client, ch, kind))) == 1


# =====================================================================
# The coordinator's whole job, using the existing management APIs
# =====================================================================
def test_coordinator_manages_companies_jobs_and_applications_end_to_end(client, ch, cohort, demo):
    company = client.post(f"{API}/companies", headers=ch, json={"name": "Phase Thirteen Labs", "industry": "Testing"}).json()
    skills = {s["name"]: s["id"] for s in client.get(f"{API}/skills", headers=ch).json()}
    new_job = client.post(f"{API}/jobs", headers=ch, json={
        "company_id": company["id"], "title": "Test Engineer", "min_cgpa": 6, "deadline": (date.today() + timedelta(days=20)).isoformat(),
        "skills": [{"skill_id": skills["Python"], "importance": "required", "weight": 3}]})
    assert new_job.status_code == 201
    jid = new_job.json()["id"]
    student = cohort["farah"]
    applied = client.post(f"{API}/applications", headers=token_for(student.user), json={"job_id": jid})
    assert applied.status_code == 201

    by_company = client.get(f"{API}/applications", headers=ch, params={"company_id": company["id"]}).json()
    assert by_company["total"] == 1 and by_company["items"][0]["student"]["full_name"] == "Farah Khan"
    assert client.get(f"{API}/applications", headers=ch, params={"job_id": jid, "status": "applied"}).json()["total"] == 1
    assert client.get(f"{API}/applications", headers=ch, params={"job_id": jid, "status": "selected"}).json()["total"] == 0

    app_id = applied.json()["id"]
    for new_status in ("shortlisted", "selected"):
        assert client.patch(f"{API}/applications/{app_id}/status", headers=ch, json={"status": new_status}).json()["status"] == new_status
    stats = get(client, ch, "/dashboard")["stats"]
    assert stats["selected_students"] == 2 and stats["total_applications"] == 8 and stats["total_jobs"] == 20 and stats["total_companies"] == 11
    farah = get(client, ch, f"/students/{student.id}")
    assert farah["stage"] == "placed" and farah["applications"]["items"][0]["status"] == "selected"

    assert client.put(f"{API}/jobs/{jid}", headers=ch, json={**new_job.json(), "company_id": company["id"], "title": "Senior Test Engineer", "min_cgpa": 6.5,
                      "skills": [{"skill_id": skills["Python"], "importance": "required", "weight": 3}], "allowed_branch_ids": [], "required_certifications": []}).status_code == 200
    assert client.delete(f"{API}/jobs/{jid}", headers=ch).status_code == 409  # it has an application: protected from deletion
    assert client.delete(f"{API}/companies/{company['id']}", headers=ch).status_code == 409
