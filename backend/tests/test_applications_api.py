"""API tests: applications, status updates, interviews and who may do what."""
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.database.seed_demo import seed_demo_data
from app.models import Application, ApplicationStatus, Job
from tests.conftest import STUDENT, auth_header

API = "/api/v1"
APPS = f"{API}/applications"
IVS = f"{API}/interviews"
ME = f"{API}/students/me"
OTHER = {"full_name": "Ravi Kumar", "email": "ravi@example.com", "password": "Passw0rd123"}


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


def jid(db, title="Data Analyst"):
    return db.scalar(select(Job.id).where(Job.title == title))


def apply(client, h, job_id):
    return client.post(APPS, headers=h, json={"job_id": job_id})


def make_app(client, h, db, title="Data Analyst"):
    res = apply(client, h, jid(db, title))
    assert res.status_code == 201, res.text
    return res.json()


def iso(delta_days=0, hours=0):
    return (datetime.now().replace(microsecond=0) + timedelta(days=delta_days, hours=hours)).isoformat()


def add_iv(client, h, app_id, **fields):
    body = {"stage": "technical_interview", **fields}
    res = client.post(f"{APPS}/{app_id}/interviews", headers=h, json=body)
    assert res.status_code == 201, res.text
    return res.json()


# =====================================================================
# Apply
# =====================================================================
def test_apply_creates_an_application(client, h, demo):
    res = apply(client, h, jid(demo))
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "applied" and body["can_withdraw"] is True and body["interview_count"] == 0
    assert body["job"]["title"] == "Data Analyst" and body["job"]["company"] == "Aurora Analytics"
    assert body["student"]["email"] == STUDENT["email"] and body["student"]["full_name"] == STUDENT["full_name"]
    assert body["interviews"] == [] and body["next_interview"] is None
    assert demo.scalar(select(func.count()).select_from(Application)) == 1


def test_apply_includes_the_live_eligibility_but_does_not_block(client, h, demo):
    body = make_app(client, h, demo)  # a brand-new student with no CGPA, branch or skills
    assert body["eligibility_now"]["eligible"] is False
    assert body["eligibility_now"]["result"] == "NOT_ELIGIBLE" and "Required skills" in body["eligibility_now"]["failed_requirements"]
    assert body["eligibility_now"]["criteria"]


def test_duplicate_application_is_rejected(client, h, demo):
    first = make_app(client, h, demo)
    res = apply(client, h, jid(demo))
    assert res.status_code == 409 and res.json()["detail"] == "You have already applied to this job."
    assert demo.scalar(select(func.count()).select_from(Application)) == 1
    assert client.get(f"{APPS}/me", headers=h).json()["total"] == 1 and first["id"]


def test_duplicate_is_rejected_whatever_the_current_status(client, h, ch, demo):
    app = make_app(client, h, demo)
    client.patch(f"{APPS}/{app['id']}/status", headers=ch, json={"status": "shortlisted"})
    assert apply(client, h, jid(demo)).status_code == 409


def test_different_students_can_apply_to_the_same_job(client, h, other_h, demo):
    make_app(client, h, demo)
    assert apply(client, other_h, jid(demo)).status_code == 201
    assert demo.scalar(select(func.count()).select_from(Application)) == 2


def test_one_student_can_apply_to_several_jobs(client, h, demo):
    make_app(client, h, demo, "Data Analyst")
    make_app(client, h, demo, "Security Analyst")
    assert client.get(f"{APPS}/me", headers=h).json()["total"] == 2


def test_apply_to_unknown_or_closed_job_is_not_found(client, h, demo):
    assert apply(client, h, 99999).status_code == 404
    closed = demo.scalar(select(Job.id).where(Job.status == "closed"))
    assert apply(client, h, closed).status_code == 404


def test_apply_after_the_deadline_is_rejected(client, h, demo):
    job = demo.get(Job, jid(demo))
    job.deadline = date.today() - timedelta(days=1)
    demo.commit()
    res = apply(client, h, job.id)
    assert res.status_code == 409 and "deadline" in res.json()["detail"]
    assert demo.scalar(select(func.count()).select_from(Application)) == 0


def test_apply_validation(client, h):
    assert client.post(APPS, headers=h, json={}).status_code == 422
    assert client.post(APPS, headers=h, json={"job_id": "abc"}).status_code == 422


# =====================================================================
# Viewing applications
# =====================================================================
def test_my_applications_lists_only_my_own_with_counts(client, h, other_h, ch, demo):
    a = make_app(client, h, demo, "Data Analyst")
    make_app(client, h, demo, "Security Analyst")
    make_app(client, other_h, demo, "Data Analyst")
    client.patch(f"{APPS}/{a['id']}/status", headers=ch, json={"status": "shortlisted"})
    body = client.get(f"{APPS}/me", headers=h).json()
    assert body["total"] == 2 and {i["student"]["email"] for i in body["items"]} == {STUDENT["email"]}
    assert body["counts"] == {"shortlisted": 1, "applied": 1}
    assert [i["job"]["title"] for i in body["items"]] == ["Security Analyst", "Data Analyst"]  # newest first
    only = client.get(f"{APPS}/me", headers=h, params={"status": "shortlisted"}).json()
    assert [i["id"] for i in only["items"]] == [a["id"]] and only["counts"] == {"shortlisted": 1, "applied": 1}
    by_job = client.get(f"{APPS}/me", headers=h, params={"job_id": jid(demo, "Security Analyst")}).json()
    assert by_job["total"] == 1 and by_job["items"][0]["job"]["title"] == "Security Analyst"
    assert client.get(f"{APPS}/me", headers=h, params={"status": "bogus"}).status_code == 422


def test_a_new_student_has_no_applications(client, h):
    body = client.get(f"{APPS}/me", headers=h).json()
    assert body["items"] == [] and body["total"] == 0 and body["counts"] == {}


def test_application_detail_owner_and_coordinator(client, h, ch, demo):
    app = make_app(client, h, demo)
    own = client.get(f"{APPS}/{app['id']}", headers=h)
    assert own.status_code == 200 and own.json()["id"] == app["id"]
    assert client.get(f"{APPS}/{app['id']}", headers=ch).status_code == 200


def test_application_detail_is_hidden_from_other_students(client, h, other_h, demo):
    app = make_app(client, h, demo)
    res = client.get(f"{APPS}/{app['id']}", headers=other_h)
    assert res.status_code == 404 and res.json()["detail"] == "Application not found."
    assert client.get(f"{APPS}/99999", headers=h).status_code == 404


# =====================================================================
# Withdraw
# =====================================================================
def test_withdraw_marks_the_application_withdrawn(client, h, demo):
    app = make_app(client, h, demo)
    res = client.post(f"{APPS}/{app['id']}/withdraw", headers=h)
    assert res.status_code == 200 and res.json()["status"] == "withdrawn" and res.json()["can_withdraw"] is False
    assert client.get(f"{APPS}/{app['id']}", headers=h).json()["status"] == "withdrawn"
    assert demo.scalar(select(func.count()).select_from(Application)) == 1  # the record is kept


def test_cannot_withdraw_twice(client, h, demo):
    app = make_app(client, h, demo)
    client.post(f"{APPS}/{app['id']}/withdraw", headers=h)
    res = client.post(f"{APPS}/{app['id']}/withdraw", headers=h)
    assert res.status_code == 409 and "already been withdrawn" in res.json()["detail"]


@pytest.mark.parametrize("final", ["selected", "rejected"])
def test_cannot_withdraw_after_a_final_decision(client, h, ch, demo, final):
    app = make_app(client, h, demo)
    client.patch(f"{APPS}/{app['id']}/status", headers=ch, json={"status": final})
    res = client.post(f"{APPS}/{app['id']}/withdraw", headers=h)
    assert res.status_code == 409 and final in res.json()["detail"]
    assert client.get(f"{APPS}/{app['id']}", headers=h).json()["status"] == final


def test_can_withdraw_mid_process(client, h, ch, demo):
    app = make_app(client, h, demo)
    client.patch(f"{APPS}/{app['id']}/status", headers=ch, json={"status": "technical_interview"})
    assert client.post(f"{APPS}/{app['id']}/withdraw", headers=h).status_code == 200


def test_applying_again_after_withdrawing_reopens_the_same_record(client, h, demo):
    app = make_app(client, h, demo)
    client.post(f"{APPS}/{app['id']}/withdraw", headers=h)
    again = apply(client, h, jid(demo))
    assert again.status_code == 201 and again.json()["id"] == app["id"] and again.json()["status"] == "applied"
    assert demo.scalar(select(func.count()).select_from(Application)) == 1
    assert apply(client, h, jid(demo)).status_code == 409  # and the duplicate rule applies again


def test_cannot_withdraw_someone_elses_application(client, h, other_h, demo):
    app = make_app(client, h, demo)
    assert client.post(f"{APPS}/{app['id']}/withdraw", headers=other_h).status_code == 404
    assert client.get(f"{APPS}/{app['id']}", headers=h).json()["status"] == "applied"


# =====================================================================
# Status updates (coordinator)
# =====================================================================
@pytest.mark.parametrize("new", ["shortlisted", "online_assessment", "technical_interview", "hr_interview", "selected", "rejected", "applied"])
def test_coordinator_can_set_every_official_status(client, h, ch, demo, new):
    app = make_app(client, h, demo)
    res = client.patch(f"{APPS}/{app['id']}/status", headers=ch, json={"status": new})
    assert res.status_code == 200 and res.json()["status"] == new
    assert client.get(f"{APPS}/{app['id']}", headers=h).json()["status"] == new  # the student sees it


def test_status_can_progress_through_the_whole_process(client, h, ch, demo):
    app = make_app(client, h, demo)
    for step in ("shortlisted", "online_assessment", "technical_interview", "hr_interview", "selected"):
        assert client.patch(f"{APPS}/{app['id']}/status", headers=ch, json={"status": step}).json()["status"] == step


def test_students_cannot_change_the_official_status(client, h, demo):
    app = make_app(client, h, demo)
    res = client.patch(f"{APPS}/{app['id']}/status", headers=h, json={"status": "selected"})
    assert res.status_code == 403
    assert client.get(f"{APPS}/{app['id']}", headers=h).json()["status"] == "applied"


def test_status_update_validation_and_rules(client, h, ch, demo):
    app = make_app(client, h, demo)
    assert client.patch(f"{APPS}/{app['id']}/status", headers=ch, json={"status": "hired"}).status_code == 422
    assert client.patch(f"{APPS}/{app['id']}/status", headers=ch, json={}).status_code == 422
    res = client.patch(f"{APPS}/{app['id']}/status", headers=ch, json={"status": "withdrawn"})
    assert res.status_code == 422 and "Only the student" in res.json()["detail"]
    assert client.patch(f"{APPS}/99999/status", headers=ch, json={"status": "selected"}).status_code == 404


def test_withdrawn_applications_cannot_be_changed_by_a_coordinator(client, h, ch, demo):
    app = make_app(client, h, demo)
    client.post(f"{APPS}/{app['id']}/withdraw", headers=h)
    res = client.patch(f"{APPS}/{app['id']}/status", headers=ch, json={"status": "selected"})
    assert res.status_code == 409 and "withdrew" in res.json()["detail"]


# =====================================================================
# Coordinator overview
# =====================================================================
def test_coordinator_sees_every_students_applications(client, h, other_h, ch, demo):
    make_app(client, h, demo, "Data Analyst")
    make_app(client, other_h, demo, "Security Analyst")
    body = client.get(APPS, headers=ch).json()
    assert body["total"] == 2 and {i["student"]["email"] for i in body["items"]} == {STUDENT["email"], OTHER["email"]}
    assert body["counts"] == {"applied": 2}
    item = body["items"][0]
    assert {"id", "full_name", "email", "branch", "cgpa"} <= set(item["student"])


def test_coordinator_filters_and_search(client, h, other_h, ch, demo):
    a = make_app(client, h, demo, "Data Analyst")
    make_app(client, other_h, demo, "Security Analyst")
    client.patch(f"{APPS}/{a['id']}/status", headers=ch, json={"status": "selected"})
    assert client.get(APPS, headers=ch, params={"status": "selected"}).json()["total"] == 1
    assert client.get(APPS, headers=ch, params={"status": "selected"}).json()["counts"] == {"selected": 1, "applied": 1}
    assert client.get(APPS, headers=ch, params={"job_id": jid(demo, "Security Analyst")}).json()["total"] == 1
    assert client.get(APPS, headers=ch, params={"q": "ravi"}).json()["total"] == 1
    assert client.get(APPS, headers=ch, params={"q": "helix"}).json()["items"][0]["job"]["company"] == "Helix Secure"
    assert client.get(APPS, headers=ch, params={"q": "%"}).json()["total"] == 0  # wildcards are literal
    assert client.get(APPS, headers=ch, params={"q": "nobody"}).json()["items"] == []


def test_coordinator_list_pagination(client, h, ch, demo):
    for title in ("Data Analyst", "Security Analyst", "Android Developer"):
        make_app(client, h, demo, title)
    page1 = client.get(APPS, headers=ch, params={"limit": 2}).json()
    page2 = client.get(APPS, headers=ch, params={"limit": 2, "offset": 2}).json()
    assert page1["total"] == page2["total"] == 3 and len(page1["items"]) == 2 and len(page2["items"]) == 1
    assert client.get(APPS, headers=ch, params={"limit": 0}).status_code == 422


def test_students_cannot_list_all_applications(client, h, demo):
    assert client.get(APPS, headers=h).status_code == 403


# =====================================================================
# Interviews: create
# =====================================================================
def test_create_interview(client, h, demo):
    app = make_app(client, h, demo)
    when = iso(3)
    iv = add_iv(client, h, app["id"], stage="technical_interview", scheduled_at=when, notes="Bring laptop. Topics: SQL, Python.")
    assert iv["stage"] == "technical_interview" and iv["scheduled_at"] == when
    assert iv["outcome"] == "pending" and iv["notes"] == "Bring laptop. Topics: SQL, Python."
    assert iv["is_upcoming"] is True and iv["needs_result"] is False and iv["application_id"] == app["id"]
    detail = client.get(f"{APPS}/{app['id']}", headers=h).json()
    assert detail["interview_count"] == 1 and detail["next_interview"] == when and detail["interviews"][0]["id"] == iv["id"]


def test_create_interview_without_a_date_is_unscheduled(client, h, demo):
    iv = add_iv(client, h, make_app(client, h, demo)["id"], stage="online_assessment")
    assert iv["scheduled_at"] is None and iv["is_upcoming"] is False and iv["needs_result"] is False


def test_recording_a_past_interview_without_a_result_is_flagged(client, h, demo):
    iv = add_iv(client, h, make_app(client, h, demo)["id"], scheduled_at=iso(-2))
    assert iv["is_upcoming"] is False and iv["needs_result"] is True
    done = add_iv(client, h, make_app(client, h, demo, "Security Analyst")["id"], scheduled_at=iso(-2), outcome="passed")
    assert done["needs_result"] is False and done["outcome"] == "passed"


@pytest.mark.parametrize("stage", ["online_assessment", "technical_interview", "hr_interview", "other"])
def test_every_stage_type_is_accepted(client, h, demo, stage):
    assert add_iv(client, h, make_app(client, h, demo)["id"], stage=stage)["stage"] == stage


@pytest.mark.parametrize("bad", [
    {"stage": "coffee_chat"}, {"stage": None}, {"scheduled_at": "tomorrow-ish"}, {"scheduled_at": "1850-01-01T10:00:00"},
    {"scheduled_at": "2500-01-01T10:00:00"}, {"outcome": "great"}, {"notes": "x" * 2001},
])
def test_interview_validation(client, h, demo, bad):
    app = make_app(client, h, demo)
    res = client.post(f"{APPS}/{app['id']}/interviews", headers=h, json={"stage": "hr_interview", **bad})
    assert res.status_code == 422


def test_interview_requires_a_stage(client, h, demo):
    app = make_app(client, h, demo)
    assert client.post(f"{APPS}/{app['id']}/interviews", headers=h, json={"notes": "hi"}).status_code == 422


def test_blank_notes_are_stored_as_nothing(client, h, demo):
    assert add_iv(client, h, make_app(client, h, demo)["id"], notes="   ")["notes"] is None


def test_cannot_add_interviews_to_other_students_applications(client, h, other_h, demo):
    app = make_app(client, h, demo)
    res = client.post(f"{APPS}/{app['id']}/interviews", headers=other_h, json={"stage": "hr_interview"})
    assert res.status_code == 404
    assert client.get(f"{APPS}/{app['id']}", headers=h).json()["interview_count"] == 0
    assert client.post(f"{APPS}/99999/interviews", headers=h, json={"stage": "hr_interview"}).status_code == 404


def test_cannot_add_interviews_to_a_withdrawn_application(client, h, demo):
    app = make_app(client, h, demo)
    client.post(f"{APPS}/{app['id']}/withdraw", headers=h)
    res = client.post(f"{APPS}/{app['id']}/interviews", headers=h, json={"stage": "hr_interview"})
    assert res.status_code == 409 and "withdrawn" in res.json()["detail"]


def test_coordinator_can_schedule_an_interview_for_any_application(client, h, ch, demo):
    app = make_app(client, h, demo)
    iv = add_iv(client, ch, app["id"], stage="online_assessment", scheduled_at=iso(5))
    assert client.get(f"{IVS}/me", headers=h).json()["items"][0]["id"] == iv["id"]  # and the student sees it


# =====================================================================
# Interviews: update, delete, view
# =====================================================================
def test_update_interview_partially(client, h, demo):
    app = make_app(client, h, demo)
    iv = add_iv(client, h, app["id"], stage="technical_interview", scheduled_at=iso(2), notes="first notes")
    res = client.patch(f"{IVS}/{iv['id']}", headers=h, json={"notes": "Went well; asked about joins."})
    assert res.status_code == 200
    body = res.json()
    assert body["notes"] == "Went well; asked about joins."
    assert body["stage"] == "technical_interview" and body["scheduled_at"] == iv["scheduled_at"] and body["outcome"] == "pending"


def test_update_interview_result_stage_and_date(client, h, demo):
    iv = add_iv(client, h, make_app(client, h, demo)["id"], scheduled_at=iso(-1))
    assert iv["needs_result"] is True
    res = client.patch(f"{IVS}/{iv['id']}", headers=h, json={"outcome": "passed", "stage": "hr_interview"}).json()
    assert res["outcome"] == "passed" and res["stage"] == "hr_interview" and res["needs_result"] is False
    new_date = iso(7)
    moved = client.patch(f"{IVS}/{iv['id']}", headers=h, json={"scheduled_at": new_date}).json()
    assert moved["scheduled_at"] == new_date and moved["is_upcoming"] is True
    assert client.get(f"{IVS}/{iv['id']}", headers=h).json()["scheduled_at"] == new_date  # persisted


def test_update_can_clear_the_date_and_the_notes(client, h, demo):
    iv = add_iv(client, h, make_app(client, h, demo)["id"], scheduled_at=iso(2), notes="x")
    cleared = client.patch(f"{IVS}/{iv['id']}", headers=h, json={"scheduled_at": None, "notes": None}).json()
    assert cleared["scheduled_at"] is None and cleared["notes"] is None and cleared["is_upcoming"] is False


def test_update_validation(client, h, demo):
    iv = add_iv(client, h, make_app(client, h, demo)["id"])
    url = f"{IVS}/{iv['id']}"
    assert client.patch(url, headers=h, json={"stage": "nonsense"}).status_code == 422
    assert client.patch(url, headers=h, json={"outcome": "maybe"}).status_code == 422
    assert client.patch(url, headers=h, json={"scheduled_at": "not a date"}).status_code == 422
    assert client.patch(url, headers=h, json={"notes": "x" * 3000}).status_code == 422
    assert client.patch(url, headers=h, json={"stage": None}).status_code == 422
    assert client.patch(url, headers=h, json={"outcome": None}).status_code == 422
    assert client.patch(url, headers=h, json={}).status_code == 200  # nothing to change is fine
    assert client.get(url, headers=h).json()["stage"] == "technical_interview"


def test_cannot_update_or_delete_other_students_interviews(client, h, other_h, demo):
    iv = add_iv(client, h, make_app(client, h, demo)["id"], notes="private")
    assert client.patch(f"{IVS}/{iv['id']}", headers=other_h, json={"notes": "hacked"}).status_code == 404
    assert client.delete(f"{IVS}/{iv['id']}", headers=other_h).status_code == 404
    assert client.get(f"{IVS}/{iv['id']}", headers=other_h).status_code == 404
    assert client.get(f"{IVS}/{iv['id']}", headers=h).json()["notes"] == "private"


def test_unknown_interview_is_404(client, h):
    assert client.get(f"{IVS}/99999", headers=h).status_code == 404
    assert client.patch(f"{IVS}/99999", headers=h, json={"notes": "x"}).status_code == 404
    assert client.delete(f"{IVS}/99999", headers=h).status_code == 404


def test_cannot_update_interviews_of_a_withdrawn_application(client, h, demo):
    app = make_app(client, h, demo)
    iv = add_iv(client, h, app["id"])
    client.post(f"{APPS}/{app['id']}/withdraw", headers=h)
    assert client.patch(f"{IVS}/{iv['id']}", headers=h, json={"notes": "late"}).status_code == 409


def test_delete_interview(client, h, demo):
    app = make_app(client, h, demo)
    iv = add_iv(client, h, app["id"])
    assert client.delete(f"{IVS}/{iv['id']}", headers=h).status_code == 204
    assert client.get(f"{IVS}/{iv['id']}", headers=h).status_code == 404
    assert client.get(f"{APPS}/{app['id']}", headers=h).json()["interview_count"] == 0


def test_interview_detail_includes_job_and_application_context(client, h, ch, demo):
    app = make_app(client, h, demo)
    iv = add_iv(client, h, app["id"], stage="hr_interview", scheduled_at=iso(1), notes="Panel of two")
    body = client.get(f"{IVS}/{iv['id']}", headers=h).json()
    assert body["application"]["job"]["title"] == "Data Analyst" and body["application"]["job"]["company"] == "Aurora Analytics"
    assert body["application"]["status"] == "applied" and body["student"]["email"] == STUDENT["email"]
    assert client.get(f"{IVS}/{iv['id']}", headers=ch).status_code == 200


def test_deleting_the_user_removes_applications_and_interviews(client, h, demo):
    from app.models import InterviewStage, User

    add_iv(client, h, make_app(client, h, demo)["id"])
    demo.delete(demo.scalar(select(User).where(User.email == STUDENT["email"])))
    demo.commit()
    assert demo.scalar(select(func.count()).select_from(Application)) == 0
    assert demo.scalar(select(func.count()).select_from(InterviewStage)) == 0


# =====================================================================
# Interviews: upcoming / past lists
# =====================================================================
def seed_interviews(client, h, demo):
    a = make_app(client, h, demo, "Data Analyst")["id"]
    b = make_app(client, h, demo, "Security Analyst")["id"]
    return {
        "late": add_iv(client, h, a, scheduled_at=iso(10), stage="hr_interview"),
        "soon": add_iv(client, h, b, scheduled_at=iso(1), stage="online_assessment"),
        "old": add_iv(client, h, a, scheduled_at=iso(-10), outcome="passed"),
        "recent": add_iv(client, h, b, scheduled_at=iso(-1)),  # pending -> needs a result
        "tbd": add_iv(client, h, a, stage="other"),
    }


def ids(page):
    return [i["id"] for i in page["items"]]


def test_upcoming_interviews_are_soonest_first(client, h, demo):
    iv = seed_interviews(client, h, demo)
    page = client.get(f"{IVS}/me", headers=h, params={"when": "upcoming"}).json()
    assert ids(page) == [iv["soon"]["id"], iv["late"]["id"]] and page["total"] == 2


def test_past_interviews_are_most_recent_first(client, h, demo):
    iv = seed_interviews(client, h, demo)
    page = client.get(f"{IVS}/me", headers=h, params={"when": "past"}).json()
    assert ids(page) == [iv["recent"]["id"], iv["old"]["id"]]


def test_unscheduled_interviews(client, h, demo):
    iv = seed_interviews(client, h, demo)
    assert ids(client.get(f"{IVS}/me", headers=h, params={"when": "unscheduled"}).json()) == [iv["tbd"]["id"]]


def test_all_interviews_and_counts(client, h, demo):
    iv = seed_interviews(client, h, demo)
    page = client.get(f"{IVS}/me", headers=h).json()
    assert ids(page) == [iv["soon"]["id"], iv["late"]["id"], iv["recent"]["id"], iv["old"]["id"], iv["tbd"]["id"]]
    assert page["counts"] == {"upcoming": 2, "past": 2, "unscheduled": 1, "needs_result": 1}
    first = page["items"][0]
    assert first["application"]["job"]["company"] == "Helix Secure" and first["application"]["job"]["title"] == "Security Analyst"


def test_a_just_scheduled_interview_moves_from_upcoming_to_past_with_time(client, h, demo):
    iv = add_iv(client, h, make_app(client, h, demo)["id"], scheduled_at=iso(0, hours=1))
    assert ids(client.get(f"{IVS}/me", headers=h, params={"when": "upcoming"}).json()) == [iv["id"]]
    client.patch(f"{IVS}/{iv['id']}", headers=h, json={"scheduled_at": iso(0, hours=-1)})
    assert ids(client.get(f"{IVS}/me", headers=h, params={"when": "upcoming"}).json()) == []
    assert ids(client.get(f"{IVS}/me", headers=h, params={"when": "past"}).json()) == [iv["id"]]


def test_each_student_only_sees_their_own_interviews(client, h, other_h, demo):
    add_iv(client, h, make_app(client, h, demo)["id"], scheduled_at=iso(1))
    assert client.get(f"{IVS}/me", headers=other_h).json()["items"] == []
    mine = client.get(f"{IVS}/me", headers=h).json()
    assert mine["total"] == 1


def test_application_detail_orders_interviews_by_date_with_unscheduled_last(client, h, demo):
    app = make_app(client, h, demo)["id"]
    c = add_iv(client, h, app)
    b = add_iv(client, h, app, scheduled_at=iso(5))
    a = add_iv(client, h, app, scheduled_at=iso(2))
    order = [i["id"] for i in client.get(f"{APPS}/{app}", headers=h).json()["interviews"]]
    assert order == [a["id"], b["id"], c["id"]]


def test_next_interview_ignores_past_ones(client, h, demo):
    app = make_app(client, h, demo)["id"]
    add_iv(client, h, app, scheduled_at=iso(-3))
    soon = add_iv(client, h, app, scheduled_at=iso(4))
    add_iv(client, h, app, scheduled_at=iso(9))
    assert client.get(f"{APPS}/{app}", headers=h).json()["next_interview"] == soon["scheduled_at"]
    assert client.get(f"{APPS}/me", headers=h).json()["items"][0]["next_interview"] == soon["scheduled_at"]


def test_invalid_when_filter(client, h):
    assert client.get(f"{IVS}/me", headers=h, params={"when": "someday"}).status_code == 422


def test_coordinator_sees_all_interviews(client, h, other_h, ch, demo):
    add_iv(client, h, make_app(client, h, demo)["id"], scheduled_at=iso(1))
    add_iv(client, other_h, make_app(client, other_h, demo)["id"], scheduled_at=iso(2))
    page = client.get(IVS, headers=ch, params={"when": "upcoming"}).json()
    assert page["total"] == 2 and {i["student"]["email"] for i in page["items"]} == {STUDENT["email"], OTHER["email"]}


# =====================================================================
# Authorization overview
# =====================================================================
def test_everything_requires_login(client, demo):
    assert client.post(APPS, json={"job_id": jid(demo)}).status_code == 401
    for method, url in (("get", f"{APPS}/me"), ("get", APPS), ("get", f"{APPS}/1"), ("post", f"{APPS}/1/withdraw"),
                        ("patch", f"{APPS}/1/status"), ("post", f"{APPS}/1/interviews"), ("get", f"{IVS}/me"), ("get", IVS),
                        ("get", f"{IVS}/1"), ("patch", f"{IVS}/1"), ("delete", f"{IVS}/1")):
        res = getattr(client, method)(url) if method in ("get", "delete") else getattr(client, method)(url, json={})
        assert res.status_code == 401, (method, url)


def test_coordinators_cannot_use_student_only_actions(client, h, ch, demo):
    app = make_app(client, h, demo)
    assert client.post(APPS, headers=ch, json={"job_id": jid(demo)}).status_code == 403
    assert client.get(f"{APPS}/me", headers=ch).status_code == 403
    assert client.post(f"{APPS}/{app['id']}/withdraw", headers=ch).status_code == 403
    assert client.get(f"{IVS}/me", headers=ch).status_code == 403


def test_students_cannot_use_coordinator_only_actions(client, h, demo):
    app = make_app(client, h, demo)
    assert client.get(APPS, headers=h).status_code == 403
    assert client.get(IVS, headers=h).status_code == 403
    assert client.patch(f"{APPS}/{app['id']}/status", headers=h, json={"status": "selected"}).status_code == 403


def test_application_data_never_exposes_password_hashes(client, h, ch, demo):
    app = make_app(client, h, demo)
    for headers in (h, ch):
        assert "password" not in client.get(f"{APPS}/{app['id']}", headers=headers).text.lower()
    assert "password" not in client.get(APPS, headers=ch).text.lower()


def test_status_enum_has_the_required_values():
    required = {"applied", "shortlisted", "online_assessment", "technical_interview", "hr_interview", "selected", "rejected"}
    assert required <= {s.value for s in ApplicationStatus}
