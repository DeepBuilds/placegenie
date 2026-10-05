from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Application, ApplicationStatus, Company, InterviewStage, Job, Student, User


def _application_options():
    return (
        selectinload(Application.job).selectinload(Job.company),
        selectinload(Application.student).selectinload(Student.user),
        selectinload(Application.student).selectinload(Student.branch),
        selectinload(Application.interview_stages),
    )


def get(db: Session, application_id: int) -> Application | None:
    return db.scalar(select(Application).where(Application.id == application_id).options(*_application_options()))


def get_by_student_and_job(db: Session, student_id: int, job_id: int) -> Application | None:
    return db.scalar(
        select(Application).where(Application.student_id == student_id, Application.job_id == job_id)
    )


def list_for_student(db: Session, student_id: int, status: ApplicationStatus | None, job_id: int | None) -> list[Application]:
    stmt = select(Application).where(Application.student_id == student_id)
    if status:
        stmt = stmt.where(Application.status == status)
    if job_id is not None:
        stmt = stmt.where(Application.job_id == job_id)
    return list(db.scalars(stmt.options(*_application_options()).order_by(Application.applied_at.desc(), Application.id.desc())))


def search(
    db: Session, *, status: ApplicationStatus | None, job_id: int | None, company_id: int | None,
    q: str | None, limit: int, offset: int,
) -> tuple[list[Application], int, dict[str, int]]:
    """Coordinator view over all students' applications."""
    conditions = []
    if job_id is not None:
        conditions.append(Application.job_id == job_id)
    if company_id is not None:
        conditions.append(Job.company_id == company_id)
    if q:
        pattern = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        conditions.append(or_(Student.full_name.ilike(pattern, escape="\\"), User.email.ilike(pattern, escape="\\"),
                              Job.title.ilike(pattern, escape="\\"), Company.name.ilike(pattern, escape="\\")))

    base = (
        select(Application)
        .join(Job, Job.id == Application.job_id)
        .join(Company, Company.id == Job.company_id)
        .join(Student, Student.id == Application.student_id)
        .join(User, User.id == Student.user_id)
        .where(*conditions)
    )
    counts = _counts(db, base)  # per-status totals ignore the status filter, so tabs can show all numbers
    filtered = base.where(Application.status == status) if status else base
    total = db.scalar(select(func.count()).select_from(filtered.subquery())) or 0
    rows = db.scalars(
        filtered.options(*_application_options()).order_by(Application.applied_at.desc(), Application.id.desc()).limit(limit).offset(offset)
    ).all()
    return list(rows), total, counts


def _counts(db: Session, base) -> dict[str, int]:
    sub = base.subquery()
    rows = db.execute(select(sub.c.status, func.count()).group_by(sub.c.status)).all()
    return {(s.value if hasattr(s, "value") else str(s)): n for s, n in rows}


def interviews_for_student(db: Session, student_id: int) -> list[InterviewStage]:
    return list(db.scalars(
        select(InterviewStage)
        .join(Application, Application.id == InterviewStage.application_id)
        .where(Application.student_id == student_id)
        .options(
            selectinload(InterviewStage.application).selectinload(Application.job).selectinload(Job.company),
            selectinload(InterviewStage.application).selectinload(Application.student).selectinload(Student.user),
            selectinload(InterviewStage.application).selectinload(Application.student).selectinload(Student.branch),
        )
    ))


def all_interviews(db: Session) -> list[InterviewStage]:
    return list(db.scalars(
        select(InterviewStage).options(
            selectinload(InterviewStage.application).selectinload(Application.job).selectinload(Job.company),
            selectinload(InterviewStage.application).selectinload(Application.student).selectinload(Student.user),
            selectinload(InterviewStage.application).selectinload(Application.student).selectinload(Student.branch),
        )
    ))


def get_interview(db: Session, interview_id: int) -> InterviewStage | None:
    return db.scalar(
        select(InterviewStage).where(InterviewStage.id == interview_id).options(
            selectinload(InterviewStage.application).selectinload(Application.job).selectinload(Job.company),
            selectinload(InterviewStage.application).selectinload(Application.student).selectinload(Student.user),
            selectinload(InterviewStage.application).selectinload(Application.student).selectinload(Student.branch),
        )
    )

