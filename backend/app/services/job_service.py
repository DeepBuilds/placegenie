from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    Branch,
    Company,
    Job,
    JobAllowedBranch,
    JobRequiredCertification,
    JobRole,
    JobSkill,
    JobStatus,
    Skill,
    User,
)
from app.models import Role
from app.repositories import job_repository as repo
from app.repositories import student_repository as lookups
from app.schemas.job import (
    CompanyIn,
    CompanyOut,
    JobIn,
    JobOut,
    JobPage,
    JobSkillOut,
)


def _error(code: int, detail: str) -> HTTPException:
    return HTTPException(code, detail)


# ---------- output mapping ----------
def to_job_out(job: Job) -> JobOut:
    return JobOut(
        id=job.id,
        title=job.title,
        description=job.description,
        location=job.location,
        job_type=job.job_type,
        min_cgpa=float(job.min_cgpa),
        max_backlogs=job.max_backlogs,
        min_experience_months=job.min_experience_months,
        deadline=job.deadline,
        is_expired=bool(job.deadline and job.deadline < date.today()),
        status=job.status,
        company=job.company,
        role=job.role,
        skills=[
            JobSkillOut(
                skill_id=js.skill_id,
                name=js.skill.name,
                category=js.skill.category,
                importance=js.importance,
                weight=js.weight,
            )
            # required first, then heavier weights, then name
            for js in sorted(
                job.skills,
                key=lambda s: (s.importance.value != "required", -s.weight, s.skill.name.lower()),
            )
        ],
        allowed_branches=sorted(
            [ab.branch for ab in job.allowed_branches], key=lambda b: b.name
        ),
        required_certifications=sorted(c.certification_name for c in job.required_certifications),
        created_at=job.created_at,
    )


def to_company_out(company: Company, open_jobs: int) -> CompanyOut:
    out = CompanyOut.model_validate(company)
    out.open_jobs = open_jobs
    return out


# ---------- companies ----------
def get_company_or_404(db: Session, company_id: int) -> Company:
    company = repo.get_company(db, company_id)
    if company is None:
        raise _error(status.HTTP_404_NOT_FOUND, "Company not found.")
    return company


def create_company(db: Session, data: CompanyIn) -> CompanyOut:
    if repo.get_company_by_name(db, data.name):
        raise _error(status.HTTP_409_CONFLICT, "A company with this name already exists.")
    company = Company(**data.model_dump())
    db.add(company)
    db.commit()
    return to_company_out(company, 0)


def update_company(db: Session, company_id: int, data: CompanyIn) -> CompanyOut:
    company = get_company_or_404(db, company_id)
    clash = repo.get_company_by_name(db, data.name)
    if clash and clash.id != company.id:
        raise _error(status.HTTP_409_CONFLICT, "A company with this name already exists.")
    for field, value in data.model_dump().items():
        setattr(company, field, value)
    db.commit()
    return to_company_out(company, repo.count_open_jobs(db, company.id))


def delete_company(db: Session, company_id: int) -> None:
    company = get_company_or_404(db, company_id)
    if repo.company_has_applications(db, company.id):
        raise _error(
            status.HTTP_409_CONFLICT,
            "This company has jobs with student applications and cannot be deleted. "
            "Close its jobs instead.",
        )
    db.delete(company)  # its jobs are removed by cascade
    db.commit()


# ---------- jobs ----------
def _validate_job_refs(db: Session, data: JobIn) -> None:
    if repo.get_company(db, data.company_id) is None:
        raise _error(422, "Selected company does not exist.")
    if data.role_id is not None and db.get(JobRole, data.role_id) is None:
        raise _error(422, "Selected job role does not exist.")
    skill_ids = [s.skill_id for s in data.skills]
    if len(lookups.get_by_ids(db, Skill, skill_ids)) != len(skill_ids):
        raise _error(422, "One or more selected skills do not exist.")
    if len(lookups.get_by_ids(db, Branch, data.allowed_branch_ids)) != len(data.allowed_branch_ids):
        raise _error(422, "One or more selected branches do not exist.")


def _apply_job_fields(job: Job, data: JobIn) -> None:
    scalar_fields = data.model_dump(
        exclude={"skills", "allowed_branch_ids", "required_certifications"}
    )
    for field, value in scalar_fields.items():
        setattr(job, field, value)
    job.skills = [
        JobSkill(skill_id=s.skill_id, importance=s.importance, weight=s.weight) for s in data.skills
    ]
    job.allowed_branches = [JobAllowedBranch(branch_id=b) for b in data.allowed_branch_ids]
    job.required_certifications = [
        JobRequiredCertification(certification_name=n) for n in data.required_certifications
    ]


def _reload(db: Session, job_id: int) -> JobOut:
    db.expire_all()
    return to_job_out(repo.get_job(db, job_id))


def create_job(db: Session, data: JobIn) -> JobOut:
    if data.deadline and data.deadline < date.today():
        raise _error(422, "Application deadline cannot be in the past.")
    _validate_job_refs(db, data)
    job = Job()
    _apply_job_fields(job, data)
    db.add(job)
    db.commit()
    return _reload(db, job.id)


def update_job(db: Session, job_id: int, data: JobIn) -> JobOut:
    job = repo.get_job(db, job_id)
    if job is None:
        raise _error(status.HTTP_404_NOT_FOUND, "Job not found.")
    _validate_job_refs(db, data)
    # Replace the child collections in one go: delete the old rows first so the
    # composite primary keys of the new rows cannot clash with them.
    job.skills.clear()
    job.allowed_branches.clear()
    job.required_certifications.clear()
    db.flush()
    _apply_job_fields(job, data)
    db.commit()
    return _reload(db, job_id)


def delete_job(db: Session, job_id: int) -> None:
    job = repo.get_job(db, job_id)
    if job is None:
        raise _error(status.HTTP_404_NOT_FOUND, "Job not found.")
    if repo.job_has_applications(db, job.id):
        raise _error(
            status.HTTP_409_CONFLICT,
            "This job has student applications and cannot be deleted. Set its status to closed instead.",
        )
    db.delete(job)
    db.commit()


def get_job_for(db: Session, job_id: int, user: User) -> JobOut:
    job = repo.get_job(db, job_id)
    # Students only see open jobs; drafts/closed look like "not found" to them.
    if job is None or (user.role != Role.COORDINATOR and job.status != JobStatus.OPEN):
        raise _error(status.HTTP_404_NOT_FOUND, "Job not found.")
    return to_job_out(job)


def search_jobs(db: Session, user: User, filters: repo.JobFilters, limit: int, offset: int) -> JobPage:
    if user.role != Role.COORDINATOR:
        filters.status = JobStatus.OPEN  # students cannot widen visibility via the query string
    jobs, total = repo.search_jobs(db, filters, limit, offset)
    return JobPage(items=[to_job_out(j) for j in jobs], total=total, limit=limit, offset=offset)
