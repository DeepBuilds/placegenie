from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Application,
    Company,
    Job,
    JobAllowedBranch,
    JobSkill,
    JobStatus,
    Skill,
)

SORTS = {
    "newest": [Job.created_at.desc(), Job.id.desc()],
    "deadline": [Job.deadline.is_(None), Job.deadline.asc(), Job.id.asc()],  # no-deadline last
    "cgpa_low": [Job.min_cgpa.asc(), Job.id.asc()],
    "title": [Job.title.asc(), Job.id.asc()],
}


@dataclass
class JobFilters:
    q: str | None = None
    company_id: int | None = None
    job_type: str | None = None
    role_id: int | None = None
    skill_id: int | None = None
    branch_id: int | None = None
    location: str | None = None
    max_min_cgpa: float | None = None  # only jobs whose CGPA requirement is <= this
    status: JobStatus | None = JobStatus.OPEN
    hide_expired: bool = False
    sort: str = "newest"


def _like(text: str) -> str:
    # Escape LIKE wildcards so a search for "100%" is literal.
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _load_options():
    return (
        selectinload(Job.company),
        selectinload(Job.role),
        selectinload(Job.skills).selectinload(JobSkill.skill),
        selectinload(Job.allowed_branches).selectinload(JobAllowedBranch.branch),
        selectinload(Job.required_certifications),
    )


def search_jobs(db: Session, f: JobFilters, limit: int, offset: int) -> tuple[list[Job], int]:
    conditions = []
    if f.status is not None:
        conditions.append(Job.status == f.status)
    if f.q:
        pattern = _like(f.q.strip())
        conditions.append(
            or_(
                Job.title.ilike(pattern, escape="\\"),
                Job.description.ilike(pattern, escape="\\"),
                Company.name.ilike(pattern, escape="\\"),
                exists().where(
                    JobSkill.job_id == Job.id,
                    JobSkill.skill_id.in_(select(Skill.id).where(Skill.name.ilike(pattern, escape="\\"))),
                ),
            )
        )
    if f.company_id is not None:
        conditions.append(Job.company_id == f.company_id)
    if f.job_type:
        conditions.append(Job.job_type == f.job_type)
    if f.role_id is not None:
        conditions.append(Job.role_id == f.role_id)
    if f.skill_id is not None:
        conditions.append(exists().where(JobSkill.job_id == Job.id, JobSkill.skill_id == f.skill_id))
    if f.branch_id is not None:
        # "No allowed-branch rows" means every branch is accepted.
        has_any = exists().where(JobAllowedBranch.job_id == Job.id)
        has_this = exists().where(
            JobAllowedBranch.job_id == Job.id, JobAllowedBranch.branch_id == f.branch_id
        )
        conditions.append(or_(~has_any, has_this))
    if f.location:
        conditions.append(Job.location.ilike(_like(f.location.strip()), escape="\\"))
    if f.max_min_cgpa is not None:
        conditions.append(Job.min_cgpa <= f.max_min_cgpa)
    if f.hide_expired:
        conditions.append(or_(Job.deadline.is_(None), Job.deadline >= date.today()))

    base = select(Job).join(Company, Company.id == Job.company_id).where(*conditions)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.options(*_load_options()).order_by(*SORTS.get(f.sort, SORTS["newest"])).limit(limit).offset(offset)
    ).all()
    return list(rows), total


def get_job(db: Session, job_id: int) -> Job | None:
    return db.scalar(select(Job).where(Job.id == job_id).options(*_load_options()))


def job_has_applications(db: Session, job_id: int) -> bool:
    return db.scalar(select(exists().where(Application.job_id == job_id))) or False


def company_has_applications(db: Session, company_id: int) -> bool:
    return (
        db.scalar(
            select(exists().where(Application.job_id == Job.id, Job.company_id == company_id))
        )
        or False
    )


# ---------- companies ----------
def list_companies(db: Session, q: str | None, limit: int, offset: int) -> tuple[list[tuple[Company, int]], int]:
    open_jobs = (
        select(func.count(Job.id))
        .where(Job.company_id == Company.id, Job.status == JobStatus.OPEN)
        .correlate(Company)
        .scalar_subquery()
    )
    stmt = select(Company, open_jobs)
    if q:
        pattern = _like(q.strip())
        stmt = stmt.where(
            or_(Company.name.ilike(pattern, escape="\\"), Company.industry.ilike(pattern, escape="\\"))
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.order_by(Company.name).limit(limit).offset(offset)).all()
    return [(c, n) for c, n in rows], total


def get_company(db: Session, company_id: int) -> Company | None:
    return db.get(Company, company_id)


def count_open_jobs(db: Session, company_id: int) -> int:
    return (
        db.scalar(
            select(func.count(Job.id)).where(Job.company_id == company_id, Job.status == JobStatus.OPEN)
        )
        or 0
    )


def get_company_by_name(db: Session, name: str) -> Company | None:
    return db.scalar(select(Company).where(func.lower(Company.name) == name.lower()))


def skill_demand(db: Session) -> tuple[dict[int, int], int]:
    """How many currently open jobs (deadline not passed) ask for each skill, and how many such jobs exist."""
    still_open = and_(Job.status == JobStatus.OPEN, or_(Job.deadline.is_(None), Job.deadline >= date.today()))
    total = db.scalar(select(func.count(Job.id)).where(still_open)) or 0
    rows = db.execute(
        select(JobSkill.skill_id, func.count(JobSkill.job_id))
        .join(Job, Job.id == JobSkill.job_id)
        .where(still_open)
        .group_by(JobSkill.skill_id)
    ).all()
    return {skill_id: count for skill_id, count in rows}, total
