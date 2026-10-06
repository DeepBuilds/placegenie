"""No endpoint may run one extra SQL query per row (the "N+1" problem): the number of statements is
measured with a small and a larger data set and must not grow with the data."""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import event, select

from app.database.seed_demo import seed_demo_data
from app.models import Application, ApplicationStatus, InterviewStage, InterviewStageType, Job, StageOutcome
from tests.conftest import auth_header
from tests.test_coordinator_api import CSE, make_student, token_for

API = "/api/v1"
STUDENT_PAGES = ["/jobs?limit=20", "/companies", "/recommendations", "/applications/me", "/interviews/me", "/dashboard", "/reports/me", "/chat/conversations"]
COORDINATOR_PAGES = ["/applications?limit=50", "/interviews", "/coordinators/students?limit=100", "/coordinators/dashboard", "/coordinators/analytics",
                     "/coordinators/progress", "/coordinators/report", "/coordinators/reports/applications.csv", "/jobs?limit=50"]


def count(db, call):
    seen = []
    engine = db.get_bind()

    def listener(conn, cursor, statement, *rest):
        seen.append(statement)

    event.listen(engine, "before_cursor_execute", listener)
    try:
        res = call()
    finally:
        event.remove(engine, "before_cursor_execute", listener)
    assert res.status_code == 200, res.text
    return len(seen)


def add_students(db, n, offset):
    """n students, each with 3 applications (one with two interviews) and some skills."""
    jobs = list(db.scalars(select(Job).where(Job.status == "open").order_by(Job.id)))
    students = []
    for i in range(n):
        s = make_student(db, f"Load Student {offset + i:03d}", CSE, 6.5 + (i % 3), year=3, skills=("Python", "SQL"), resume=True, project=True)
        for k in range(3):
            app = Application(student_id=s.id, job_id=jobs[(i + k) % len(jobs)].id, status=list(ApplicationStatus)[(i + k) % 7])
            db.add(app)
            db.flush()
            if k == 0:
                for d in (-3, 4):
                    db.add(InterviewStage(application_id=app.id, stage=InterviewStageType.TECHNICAL_INTERVIEW,
                                          scheduled_at=datetime.now() + timedelta(days=d), outcome=StageOutcome.PENDING))
        students.append(s)
    db.commit()
    return students


@pytest.fixture
def world(db_session):
    seed_demo_data(db_session)
    return db_session


@pytest.mark.parametrize("path", STUDENT_PAGES)
def test_student_pages_do_not_query_per_row(client, world, path):
    me = add_students(world, 1, 0)[0]
    h = token_for(me.user)
    small = count(world, lambda: client.get(API + path, headers=h))
    add_students(world, 8, 100)  # other students' data must not slow this student's pages
    for _ in range(4):  # and more of the student's own applications neither
        job = world.scalar(select(Job).where(Job.status == "open", ~Job.id.in_(select(Application.job_id).where(Application.student_id == me.id))).limit(1))
        world.add(Application(student_id=me.id, job_id=job.id, status=ApplicationStatus.SHORTLISTED))
    world.commit()
    large = count(world, lambda: client.get(API + path, headers=h))
    assert large <= small, f"{path}: {small} queries before, {large} after adding data"


@pytest.mark.parametrize("path", COORDINATOR_PAGES)
def test_coordinator_pages_do_not_query_per_row(client, world, coordinator_token, path):
    h = auth_header(coordinator_token)
    add_students(world, 2, 0)
    small = count(world, lambda: client.get(API + path, headers=h))
    add_students(world, 10, 100)
    large = count(world, lambda: client.get(API + path, headers=h))
    assert large <= small, f"{path}: {small} queries for 2 students, {large} for 12"
