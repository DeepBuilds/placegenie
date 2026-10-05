"""Phase 14: the student report and the coordinator report, checked against known sample data.

The cohort comes from test_coordinator_api (7 students, 7 applications, 3 interviews), so every expected
number below can be worked out by hand from that setup.
"""
import csv
import io
from datetime import date

import pytest
from sqlalchemy import event, select

from app.models import Skill
from app.repositories import job_repository
from tests.conftest import auth_header
from tests.test_coordinator_api import CO, CSE, IT, apply, cohort, demo, make_student, token_for  # noqa: F401 - fixtures

API = "/api/v1"


def student_report(client, student):
    res = client.get(f"{API}/reports/me", headers=token_for(student.user))
    assert res.status_code == 200, res.text
    return res.json()


def coordinator_report(client, ch):
    res = client.get(f"{CO}/report", headers=ch)
    assert res.status_code == 200, res.text
    return res.json()


@pytest.fixture
def ch(coordinator_token):
    return auth_header(coordinator_token)


def counts(report):
    return {row["status"]: row["count"] for row in report["status_distribution"]}


# =====================================================================
# Student report: known numbers
# =====================================================================
def test_report_of_a_student_in_the_middle_of_the_process(client, cohort):
    r = student_report(client, cohort["bhavna"])  # Data Scientist (shortlisted) + Security Analyst (applied)
    assert r["student"]["name"] == "Bhavna Rao" and r["student"]["branch"] == CSE
    assert r["summary"] == {"total": 2, "active": 2, "awaiting_review": 1, "in_process": 1, "selected": 0, "rejected": 0, "withdrawn": 0,
                            "outcome": "in_process", "outcome_label": "In the selection process"}
    assert counts(r) == {"applied": 1, "shortlisted": 1, "online_assessment": 0, "technical_interview": 0, "hr_interview": 0, "selected": 0, "rejected": 0, "withdrawn": 0}
    assert {(a["job_title"], a["status"]) for a in r["applications"]} == {("Data Scientist", "shortlisted"), ("Security Analyst", "applied")}
    assert r["interviews"] == {"total": 0, "passed": 0, "not_cleared": 0, "pending": 0, "upcoming": 0, "pass_rate": None, "items": []}
    assert r["errors"] == {}


def test_report_of_a_selected_student(client, cohort):
    r = student_report(client, cohort["asha"])
    assert r["summary"]["outcome"] == "placed" and r["summary"]["selected"] == 1 and r["summary"]["rejected"] == 0
    assert r["applications"][0]["company"] == "Aurora Analytics" and r["applications"][0]["status"] == "selected" and r["applications"][0]["interviews"] == 1
    assert r["interviews"]["passed"] == 1 and r["interviews"]["pass_rate"] == 100
    assert [m["done"] for m in r["progress"]["milestones"]][2:] == [True, True, True, True]  # applied, shortlisted+, interviewed, selected


def test_report_of_a_rejected_student(client, cohort):
    r = student_report(client, cohort["chirag"])
    assert r["summary"]["outcome"] == "rejected" and r["summary"]["rejected"] == 1 and r["summary"]["selected"] == 0
    assert counts(r)["rejected"] == 1


def test_interview_results_and_pass_rate(client, cohort):
    r = student_report(client, cohort["dev"])  # one failed round in the past, one HR round booked for next week
    iv = r["interviews"]
    assert (iv["total"], iv["passed"], iv["not_cleared"], iv["pending"], iv["upcoming"]) == (2, 0, 1, 1, 1)
    assert iv["pass_rate"] == 0  # one result recorded and it was not a pass: 0%, not "no data"
    assert {i["stage"] for i in iv["items"]} == {"technical_interview", "hr_interview"}
    assert r["applications"][0]["interviews"] == 2 and r["applications"][0]["next_interview"] is not None


def test_a_withdrawn_application_counts_as_withdrawn_not_as_progress(client, cohort):
    r = student_report(client, cohort["esha"])  # only application withdrawn
    assert r["summary"]["total"] == 1 and r["summary"]["active"] == 0 and r["summary"]["withdrawn"] == 1
    assert r["summary"]["outcome"] == "not_applied" and r["progress"]["milestones"][2]["done"] is False
    assert r["applications"][0]["status"] == "withdrawn"


def test_report_of_a_student_with_no_activity(client, cohort):
    r = student_report(client, cohort["farah"])
    assert r["summary"]["total"] == 0 and r["summary"]["outcome"] == "not_applied"
    assert all(v == 0 for v in counts(r).values()) and r["applications"] == []
    assert r["interviews"]["total"] == 0 and r["interviews"]["pass_rate"] is None
    assert r["progress"]["done"] == 0 and r["recommended"]["open_jobs"] == 18


def test_student_report_agrees_with_the_students_own_pages(client, cohort):
    for key in ("asha", "bhavna", "dev", "farah"):
        s = cohort[key]
        h = token_for(s.user)
        r = student_report(client, s)
        dash = client.get(f"{API}/dashboard", headers=h).json()
        assert r["recommended"] == dash["recommendations"], key
        assert r["skill_gaps"] == dash["skill_gaps"], key
        assert r["progress"] == dash["progress"], key
        mine = client.get(f"{API}/applications/me", headers=h).json()
        assert [a["id"] for a in r["applications"]] == [a["id"] for a in mine["items"]], key
        assert {k: v for k, v in counts(r).items() if v} == mine["counts"], key
        assert r["interviews"]["total"] == dash["interviews"]["total"], key
        recs = client.get(f"{API}/recommendations", headers=h).json()
        assert r["recommended"]["eligible"] == recs["counts"]["eligible"], key


def test_a_student_only_ever_sees_their_own_report(client, cohort):
    asha, bhavna = student_report(client, cohort["asha"]), student_report(client, cohort["bhavna"])
    assert asha["student"]["name"] != bhavna["student"]["name"]
    assert {a["job_title"] for a in asha["applications"]}.isdisjoint({a["job_title"] for a in bhavna["applications"]})


def test_student_report_csv(client, cohort):
    res = client.get(f"{API}/reports/me.csv", headers=token_for(cohort["asha"].user))
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/csv") and res.headers["cache-control"] == "no-store"
    assert res.headers["content-disposition"] == f'attachment; filename="placegenie-my-report-{date.today().isoformat()}.csv"'
    rows = list(csv.reader(io.StringIO(res.text.lstrip("﻿"))))
    assert rows[0] == ["Job", "Company", "Status", "Applied on", "Last updated", "Interviews recorded", "Next interview"]
    assert len(rows) == 2 and rows[1][:3] == ["Data Analyst", "Aurora Analytics", "selected"] and rows[1][5] == "1"


def test_student_report_csv_for_a_student_with_no_applications_has_only_headers(client, cohort):
    res = client.get(f"{API}/reports/me.csv", headers=token_for(cohort["farah"].user))
    assert len(list(csv.reader(io.StringIO(res.text.lstrip("﻿"))))) == 1


def test_a_student_with_nothing_at_all(client, demo, student_token):
    r = client.get(f"{API}/reports/me", headers=auth_header(student_token)).json()
    assert r["summary"]["total"] == 0 and r["interviews"]["items"] == [] and r["skill_gaps"]["student_has_skills"] is False
    assert r["recommended"]["open_jobs"] == 18


def test_student_report_on_an_empty_platform(client, student_token):
    res = client.get(f"{API}/reports/me", headers=auth_header(student_token))
    assert res.status_code == 200
    assert res.json()["recommended"]["open_jobs"] == 0 and res.json()["recommended"]["top"] == []


# =====================================================================
# Coordinator report: known numbers
# =====================================================================
def test_placement_statistics(client, ch, cohort):
    p = coordinator_report(client, ch)["placement"]
    assert (p["total_students"], p["applicants"], p["placed"], p["in_process"], p["rejected"], p["not_applied"]) == (7, 5, 1, 2, 1, 2)
    assert p["placement_rate"]["percent"] == 14 and p["placement_rate"]["sufficient_data"] is True
    assert {s["key"]: s["count"] for s in p["by_stage"]} == {"placed": 1, "in_process": 2, "applied": 1, "rejected": 1, "not_applied": 2}
    assert sum(s["count"] for s in p["by_stage"]) == p["total_students"]
    branches = {b["branch"]: b for b in p["by_branch"]}
    assert (branches[CSE]["students"], branches[CSE]["applicants"], branches[CSE]["placed"]) == (3, 2, 1) and branches[CSE]["placement_rate"] is None
    assert branches[IT]["students"] == 2 and sum(b["students"] for b in p["by_branch"]) == 7
    assert {b["band"]: b["students"] for b in p["by_cgpa"]}["8.0 - 8.9"] == 1


def test_status_distribution(client, ch, cohort):
    r = coordinator_report(client, ch)
    assert counts(r) == {"applied": 2, "shortlisted": 1, "online_assessment": 0, "technical_interview": 1, "hr_interview": 0, "selected": 1, "rejected": 1, "withdrawn": 1}
    assert sum(counts(r).values()) == 7


def test_company_wise_applications(client, ch, cohort):
    rows = {c["company"]: c for c in coordinator_report(client, ch)["companies"]}
    assert len(rows) == 10  # every company, not only the busiest
    assert rows["Aurora Analytics"] | {} == {"company": "Aurora Analytics", "jobs": 3, "applications": 1, "shortlisted": 0, "selected": 1, "rejected": 0}
    assert (rows["QuantaRetail Tech"]["applications"], rows["QuantaRetail Tech"]["shortlisted"]) == (1, 1)
    assert (rows["BrightPath Infotech"]["applications"], rows["BrightPath Infotech"]["rejected"]) == (1, 1)
    assert rows["Meridian Core Industries"]["shortlisted"] == 1  # Dev, technical interview
    assert rows["Zenith Software Labs"]["applications"] == 0
    assert sum(c["applications"] for c in rows.values()) == 7


def test_job_wise_applications(client, ch, cohort):
    jobs = coordinator_report(client, ch)["jobs"]
    assert len(jobs) == 19  # also jobs nobody applied to
    busy = [j for j in jobs if j["applications"]]
    assert [j["title"] for j in busy] == [
        "Android Developer", "Associate Software Engineer", "Data Analyst", "Data Scientist", "Graduate Engineer Trainee (Mechanical)", "Security Analyst", "Site Engineer Trainee",
    ]
    by_title = {j["title"]: j for j in jobs}
    assert by_title["Data Analyst"] | {} == {**by_title["Data Analyst"], "applications": 1, "selected": 1, "awaiting_review": 0, "in_process": 0, "rejected": 0, "withdrawn": 0}
    assert by_title["Data Scientist"]["in_process"] == 1 and by_title["Security Analyst"]["awaiting_review"] == 1
    assert by_title["Site Engineer Trainee"]["withdrawn"] == 1 and by_title["Associate Software Engineer"]["rejected"] == 1
    assert by_title["Frontend Developer (Closed Drive)"]["status"] == "closed" and by_title["Frontend Developer (Closed Drive)"]["applications"] == 0
    # every application is in exactly one column of exactly one job
    assert sum(j["applications"] for j in jobs) == 7
    for j in jobs:
        assert j["applications"] == j["awaiting_review"] + j["in_process"] + j["selected"] + j["rejected"] + j["withdrawn"], j["title"]


def test_company_and_job_tables_add_up_to_the_same_total(client, ch, cohort):
    r = coordinator_report(client, ch)
    for key in ("applications", "selected", "rejected"):
        assert sum(c[key] for c in r["companies"]) == sum(j[key] for j in r["jobs"]), key


def test_selected_students(client, ch, cohort):
    rows = coordinator_report(client, ch)["selected_students"]
    assert len(rows) == 1
    assert rows[0] | {"selected_on": None} == {"student_id": cohort["asha"].id, "name": "Asha Patil", "email": "asha.patil@example.com", "branch": CSE, "cgpa": 8.5,
                                               "company": "Aurora Analytics", "job_title": "Data Analyst", "selected_on": None}


def test_selected_students_grows_with_new_decisions(client, ch, cohort, demo):
    app = apply(demo, cohort["bhavna"], "Android Developer", "selected")
    rows = coordinator_report(client, ch)["selected_students"]
    assert {r["name"] for r in rows} == {"Asha Patil", "Bhavna Rao"}
    assert coordinator_report(client, ch)["placement"]["placed"] == 2
    assert app.id


def test_common_skill_gaps(client, ch, cohort, demo):
    gaps = coordinator_report(client, ch)["skill_gaps"]
    demand, _ = job_repository.skill_demand(demo)
    python = demo.scalar(select(Skill.id).where(Skill.name == "Python"))
    row = next(g for g in gaps if g["skill"] == "Python")
    assert row == {"skill": "Python", "jobs_requiring": demand[python], "students_with": 2, "students_lacking": 5, "percent_lacking": 71}
    assert len(gaps) <= 10
    assert [g["jobs_requiring"] for g in gaps] == sorted((g["jobs_requiring"] for g in gaps), reverse=True)
    assert all(g["students_with"] + g["students_lacking"] == 7 for g in gaps)


def test_a_skill_everyone_has_is_not_a_gap(client, ch, demo):
    for name in ("One", "Two", "Three"):
        make_student(demo, f"Everyone {name}", CSE, 8.0, skills=("Python",))
    assert "Python" not in {g["skill"] for g in coordinator_report(client, ch)["skill_gaps"]}


def test_progress_and_interviews_in_the_report(client, ch, cohort):
    r = coordinator_report(client, ch)
    assert {s["key"]: s["count"] for s in r["progress"]["funnel"]}["selected"] == 1
    assert r["interviews"] == {"total": 3, "passed": 1, "not_cleared": 1, "pending": 1, "pass_rate": 50}
    assert r["min_group_size"] == 5


def test_the_report_agrees_with_the_other_coordinator_pages(client, ch, cohort):
    r = coordinator_report(client, ch)
    dash = client.get(f"{CO}/dashboard", headers=ch).json()
    ana = client.get(f"{CO}/analytics", headers=ch).json()
    assert r["placement"]["placement_rate"] == dash["stats"]["placement_rate"]
    assert r["placement"]["placed"] == dash["stats"]["selected_students"]
    assert r["status_distribution"] == dash["application_funnel"]
    assert r["progress"] == client.get(f"{CO}/progress", headers=ch).json()
    assert r["interviews"] == ana["interview_outcomes"]
    assert r["placement"]["by_branch"] == ana["by_branch"] and r["placement"]["by_cgpa"] == ana["by_cgpa"]
    assert r["companies"][:10] == ana["by_company"]
    assert [g["skill"] for g in r["skill_gaps"]][:3] and {g["skill"] for g in r["skill_gaps"]} <= {s["skill"] for s in client.get(f"{CO}/analytics", headers=ch).json()["skill_supply"]} | {g["skill"] for g in r["skill_gaps"]}


def test_coordinator_report_with_jobs_but_no_students(client, ch, demo):
    r = coordinator_report(client, ch)
    assert r["placement"]["total_students"] == 0 and r["placement"]["placement_rate"]["percent"] is None
    assert r["placement"]["by_branch"] == [] and r["placement"]["by_cgpa"] == [] and r["selected_students"] == [] and r["skill_gaps"] == []
    assert len(r["jobs"]) == 19 and all(j["applications"] == 0 for j in r["jobs"])
    assert r["interviews"]["pass_rate"] is None and all(v == 0 for v in counts(r).values())
    assert all(s["percent"] == 0 for s in r["progress"]["funnel"])


def test_coordinator_report_on_an_empty_platform(client, ch):
    r = coordinator_report(client, ch)
    assert r["companies"] == [] and r["jobs"] == [] and r["selected_students"] == [] and r["skill_gaps"] == []
    assert r["placement"]["placement_rate"]["sufficient_data"] is False


def test_the_job_wise_csv(client, ch, cohort):
    res = client.get(f"{CO}/reports/jobs.csv", headers=ch)
    assert res.status_code == 200
    rows = list(csv.reader(io.StringIO(res.text.lstrip("﻿"))))
    assert rows[0][:2] == ["Job", "Company"] and len(rows) == 20
    da = next(r for r in rows if r[0] == "Data Analyst")
    assert da[4:] == ["1", "0", "0", "1", "0", "0"]
    assert "jobs" in [r["kind"] for r in client.get(f"{CO}/reports", headers=ch).json()]


# =====================================================================
# Authorization
# =====================================================================
def test_reports_are_limited_to_the_right_role(client, cohort, ch):
    student = token_for(cohort["asha"].user)
    assert client.get(f"{API}/reports/me").status_code == 401
    assert client.get(f"{API}/reports/me.csv").status_code == 401
    assert client.get(f"{CO}/report").status_code == 401
    assert client.get(f"{CO}/report", headers=student).status_code == 403
    assert client.get(f"{CO}/reports/jobs.csv", headers=student).status_code == 403
    assert client.get(f"{API}/reports/me", headers=ch).status_code == 403
    assert client.get(f"{API}/reports/me.csv", headers=ch).status_code == 403


# =====================================================================
# Efficient queries: the number of SQL statements must not grow with the amount of data
# =====================================================================
def count_queries(db, call):
    engine = db.get_bind()
    seen = []

    def before(conn, cursor, statement, *rest):
        seen.append(statement)

    event.listen(engine, "before_cursor_execute", before)
    try:
        call()
    finally:
        event.remove(engine, "before_cursor_execute", before)
    return len(seen)


def test_coordinator_report_query_count_does_not_grow_with_students(client, ch, cohort, demo):
    first = count_queries(demo, lambda: coordinator_report(client, ch))
    for n in range(12):
        s = make_student(demo, f"Extra Student {chr(65 + n)}", CSE, 7.0 + n / 10, skills=("Python",), resume=True, project=True)
        apply(demo, s, "Data Analyst" if n % 2 else "Data Scientist", "shortlisted")
    second = count_queries(demo, lambda: coordinator_report(client, ch))
    assert second <= first, f"{first} queries for 7 students, {second} for 19"
    assert first < 40


def test_student_report_query_count_does_not_grow_with_applications(client, cohort, demo):
    s = cohort["farah"]
    apply(demo, s, "Data Analyst", "applied")  # (eager loading adds a fixed handful of queries once a student has any application)
    call = lambda: student_report(client, s)  # noqa: E731
    first = count_queries(demo, call)
    for title in ("Data Scientist", "Security Analyst", "Android Developer", "Associate Software Engineer", "Site Engineer Trainee"):
        apply(demo, s, title, "applied")
    second = count_queries(demo, call)
    assert second <= first, f"{first} queries with one application, {second} with six"
