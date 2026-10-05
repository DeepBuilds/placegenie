"""Job applications and interview tracking.

Who may do what
  student      apply, list/view their own applications, withdraw, and record/update/delete interviews
               on their own applications
  coordinator  view every application and interview, set the official application status, and
               add/edit interviews on any application
The official application status (shortlisted, selected, ...) is only ever changed by a coordinator, so
placement statistics cannot be altered by the students they describe.
"""
from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.eligibility import check_eligibility
from app.models import (
    FINAL_STATUSES,
    Application,
    ApplicationStatus,
    InterviewStage,
    JobStatus,
    Role,
    Student,
    User,
)
from app.repositories import application_repository as repo
from app.repositories import job_repository, student_repository
from app.schemas.application import (
    ApplicationBrief,
    ApplicationDetail,
    ApplicationList,
    ApplicationSummary,
    BranchBrief,
    EligibilityNow,
    InterviewCreate,
    InterviewList,
    InterviewListItem,
    InterviewOut,
    InterviewUpdate,
    JobBrief,
    StudentBrief,
)
from app.schemas.eligibility import CriterionOut
from app.services import eligibility_service, profile_service


def _error(code: int, detail: str) -> HTTPException:
    return HTTPException(code, detail)


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


# ---------- output mapping ----------
def job_brief(job) -> JobBrief:
    return JobBrief(
        id=job.id, title=job.title, company=job.company.name, location=job.location, job_type=job.job_type,
        deadline=job.deadline, is_expired=bool(job.deadline and job.deadline < date.today()),
    )


def student_brief(student: Student) -> StudentBrief:
    return StudentBrief(
        id=student.id, full_name=student.full_name, email=student.user.email,
        branch=BranchBrief.model_validate(student.branch) if student.branch else None,
        cgpa=float(student.cgpa) if student.cgpa is not None else None,
    )


def interview_out(iv: InterviewStage, now: datetime | None = None) -> InterviewOut:
    now = now or _now()
    scheduled = iv.scheduled_at
    return InterviewOut(
        id=iv.id, application_id=iv.application_id, stage=iv.stage, scheduled_at=scheduled, outcome=iv.outcome,
        notes=iv.notes, is_upcoming=bool(scheduled and scheduled >= now),
        needs_result=bool(scheduled and scheduled < now and iv.outcome.value == "pending"),
        created_at=iv.created_at, updated_at=iv.updated_at,
    )


def can_withdraw(app: Application) -> bool:
    return app.status not in FINAL_STATUSES


def summary_out(app: Application, now: datetime | None = None) -> ApplicationSummary:
    now = now or _now()
    upcoming = [iv.scheduled_at for iv in app.interview_stages if iv.scheduled_at and iv.scheduled_at >= now]
    return ApplicationSummary(
        id=app.id, status=app.status, applied_at=app.applied_at, updated_at=app.updated_at,
        job=job_brief(app.job), student=student_brief(app.student), interview_count=len(app.interview_stages),
        next_interview=min(upcoming) if upcoming else None, can_withdraw=can_withdraw(app),
    )


def _eligibility_now(db: Session, app: Application) -> EligibilityNow:
    student = student_repository.get_profile_by_user_id(db, app.student.user_id)
    job = job_repository.get_job(db, app.job_id)
    r = check_eligibility(eligibility_service.student_snapshot(student), eligibility_service.job_snapshot(job))
    return EligibilityNow(
        result=r.result, eligible=r.eligible, summary=r.summary, failed_requirements=r.failed_requirements,
        incomplete_fields=r.incomplete_fields, criteria=[CriterionOut.model_validate(c) for c in r.criteria],
    )


def detail_out(db: Session, app: Application, now: datetime | None = None) -> ApplicationDetail:
    now = now or _now()
    interviews = sorted(app.interview_stages, key=lambda i: (i.scheduled_at is None, i.scheduled_at or now, i.id))
    return ApplicationDetail(
        **summary_out(app, now).model_dump(),
        interviews=[interview_out(i, now) for i in interviews],
        eligibility_now=_eligibility_now(db, app),
    )


# ---------- access control ----------
def get_accessible(db: Session, user: User, application_id: int) -> Application:
    """Students get only their own applications (others look 'not found'); coordinators get any."""
    app = repo.get(db, application_id)
    if app is None:
        raise _error(status.HTTP_404_NOT_FOUND, "Application not found.")
    if user.role != Role.COORDINATOR and app.student.user_id != user.id:
        raise _error(status.HTTP_404_NOT_FOUND, "Application not found.")
    return app


def get_accessible_interview(db: Session, user: User, interview_id: int) -> InterviewStage:
    iv = repo.get_interview(db, interview_id)
    if iv is None or (user.role != Role.COORDINATOR and iv.application.student.user_id != user.id):
        raise _error(status.HTTP_404_NOT_FOUND, "Interview not found.")
    return iv


# ---------- applications ----------
def apply(db: Session, user: User, job_id: int) -> ApplicationDetail:
    student = profile_service.get_student(db, user)
    job = job_repository.get_job(db, job_id)
    if job is None or job.status != JobStatus.OPEN:  # drafts/closed jobs look "not found" to students
        raise _error(status.HTTP_404_NOT_FOUND, "Job not found.")
    if job.deadline and job.deadline < date.today():
        raise _error(status.HTTP_409_CONFLICT, "The application deadline for this job has passed.")

    existing = repo.get_by_student_and_job(db, student.id, job.id)
    if existing is not None:
        if existing.status != ApplicationStatus.WITHDRAWN:
            raise _error(status.HTTP_409_CONFLICT, "You have already applied to this job.")
        existing.status = ApplicationStatus.APPLIED  # re-applying after a withdrawal re-opens the same record
        existing.applied_at = _now()
        app = existing
    else:
        app = Application(student_id=student.id, job_id=job.id, status=ApplicationStatus.APPLIED)
        db.add(app)
    try:
        db.commit()
    except IntegrityError:  # two simultaneous requests: the unique (student, job) rule wins
        db.rollback()
        raise _error(status.HTTP_409_CONFLICT, "You have already applied to this job.")
    db.expire_all()
    return detail_out(db, repo.get(db, app.id))


def list_mine(db: Session, user: User, status_filter: ApplicationStatus | None, job_id: int | None) -> ApplicationList:
    student = profile_service.get_student(db, user)
    everything = repo.list_for_student(db, student.id, None, job_id)
    counts: dict[str, int] = {}
    for a in everything:
        counts[a.status.value] = counts.get(a.status.value, 0) + 1
    shown = [a for a in everything if not status_filter or a.status == status_filter]
    now = _now()
    return ApplicationList(
        items=[summary_out(a, now) for a in shown], total=len(shown), limit=len(shown), offset=0, counts=counts
    )


def list_all(db: Session, *, status_filter, job_id, company_id, q, limit, offset) -> ApplicationList:
    rows, total, counts = repo.search(db, status=status_filter, job_id=job_id, company_id=company_id, q=q, limit=limit, offset=offset)
    now = _now()
    return ApplicationList(items=[summary_out(a, now) for a in rows], total=total, limit=limit, offset=offset, counts=counts)


def get_detail(db: Session, user: User, application_id: int) -> ApplicationDetail:
    return detail_out(db, get_accessible(db, user, application_id))


def withdraw(db: Session, user: User, application_id: int) -> ApplicationDetail:
    app = get_accessible(db, user, application_id)  # a coordinator cannot reach this: the route is student-only
    if app.status == ApplicationStatus.WITHDRAWN:
        raise _error(status.HTTP_409_CONFLICT, "This application has already been withdrawn.")
    if not can_withdraw(app):
        raise _error(status.HTTP_409_CONFLICT, f"A {app.status.value} application can no longer be withdrawn. Contact the placement cell.")
    app.status = ApplicationStatus.WITHDRAWN
    db.commit()
    db.expire_all()
    return detail_out(db, repo.get(db, application_id))


def set_status(db: Session, application_id: int, new_status: ApplicationStatus) -> ApplicationDetail:
    app = repo.get(db, application_id)
    if app is None:
        raise _error(status.HTTP_404_NOT_FOUND, "Application not found.")
    if new_status == ApplicationStatus.WITHDRAWN:
        raise _error(422, "Only the student can withdraw an application.")
    if app.status == ApplicationStatus.WITHDRAWN:
        raise _error(status.HTTP_409_CONFLICT, "The student withdrew this application; its status cannot be changed.")
    app.status = new_status
    db.commit()
    db.expire_all()
    return detail_out(db, repo.get(db, application_id))


# ---------- interviews ----------
def add_interview(db: Session, user: User, application_id: int, data: InterviewCreate) -> InterviewOut:
    app = get_accessible(db, user, application_id)
    if app.status == ApplicationStatus.WITHDRAWN:
        raise _error(status.HTTP_409_CONFLICT, "This application was withdrawn, so interviews cannot be added.")
    iv = InterviewStage(application_id=app.id, **data.model_dump())
    db.add(iv)
    db.commit()
    return interview_out(iv)


def update_interview(db: Session, user: User, interview_id: int, data: InterviewUpdate) -> InterviewOut:
    iv = get_accessible_interview(db, user, interview_id)
    if iv.application.status == ApplicationStatus.WITHDRAWN:
        raise _error(status.HTTP_409_CONFLICT, "This application was withdrawn, so its interviews cannot be changed.")
    changes = data.model_dump(exclude_unset=True)  # only what the client actually sent
    if "stage" in changes and changes["stage"] is None:
        raise _error(422, "Stage cannot be empty.")
    if "outcome" in changes and changes["outcome"] is None:
        raise _error(422, "Result cannot be empty.")
    for field, value in changes.items():
        setattr(iv, field, value)
    db.commit()
    return interview_out(iv)


def delete_interview(db: Session, user: User, interview_id: int) -> None:
    iv = get_accessible_interview(db, user, interview_id)
    db.delete(iv)
    db.commit()


def get_interview_detail(db: Session, user: User, interview_id: int) -> InterviewListItem:
    return _list_item(get_accessible_interview(db, user, interview_id), _now())


def _list_item(iv: InterviewStage, now: datetime) -> InterviewListItem:
    app = iv.application
    return InterviewListItem(
        **interview_out(iv, now).model_dump(),
        application=ApplicationBrief(id=app.id, status=app.status, job=job_brief(app.job)),
        student=student_brief(app.student),
    )


def list_interviews(db: Session, user: User, when: str = "all", now: datetime | None = None) -> InterviewList:
    """Interviews of the logged-in student (or of everyone, for a coordinator), filtered by time.

    upcoming     scheduled for now or later, soonest first
    past         scheduled earlier than now, most recent first
    unscheduled  no date set yet
    """
    now = now or _now()
    if user.role == Role.COORDINATOR:
        interviews = repo.all_interviews(db)
    else:
        interviews = repo.interviews_for_student(db, profile_service.get_student(db, user).id)

    upcoming = sorted((i for i in interviews if i.scheduled_at and i.scheduled_at >= now), key=lambda i: (i.scheduled_at, i.id))
    past = sorted((i for i in interviews if i.scheduled_at and i.scheduled_at < now), key=lambda i: (i.scheduled_at, i.id), reverse=True)
    unscheduled = sorted((i for i in interviews if i.scheduled_at is None), key=lambda i: i.id)
    counts = {
        "upcoming": len(upcoming), "past": len(past), "unscheduled": len(unscheduled),
        "needs_result": sum(1 for i in past if i.outcome.value == "pending"),
    }
    chosen = {"upcoming": upcoming, "past": past, "unscheduled": unscheduled, "all": [*upcoming, *past, *unscheduled]}[when]
    return InterviewList(items=[_list_item(i, now) for i in chosen], total=len(chosen), counts=counts)
