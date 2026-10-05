"""Glue between the database and the pure eligibility rules in app/ai/eligibility.py."""
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.eligibility import (
    ExperiencePeriod,
    JobSkillReq,
    JobSnapshot,
    StudentSnapshot,
    check_eligibility,
)
from app.models import Job, JobStatus, SkillImportance, Student, User
from app.repositories import job_repository
from app.schemas.eligibility import EligibilityOut, JobRef
from app.services import profile_service


def student_snapshot(student: Student) -> StudentSnapshot:
    return StudentSnapshot(
        cgpa=float(student.cgpa) if student.cgpa is not None else None,
        branch_id=student.branch_id,
        branch_name=student.branch.name if student.branch else None,
        backlogs=student.backlogs,
        skill_ids={s.skill_id for s in student.skills},
        certifications=[c.name for c in student.certifications],
        experiences=[ExperiencePeriod(e.start_date, e.end_date) for e in student.experiences],
    )


def job_snapshot(job: Job) -> JobSnapshot:
    return JobSnapshot(
        is_open=job.status == JobStatus.OPEN,
        deadline=job.deadline,
        min_cgpa=float(job.min_cgpa),
        max_backlogs=job.max_backlogs,
        min_experience_months=job.min_experience_months,
        allowed_branches={ab.branch_id: ab.branch.name for ab in job.allowed_branches},
        skills=[
            JobSkillReq(js.skill_id, js.skill.name, js.importance == SkillImportance.REQUIRED)
            for js in job.skills
        ],
        required_certifications=[c.certification_name for c in job.required_certifications],
    )


def check_for_student(db: Session, user: User, job_id: int, today: date | None = None) -> EligibilityOut:
    student = profile_service.get_student(db, user)
    job = job_repository.get_job(db, job_id)
    # Same visibility rule as the job pages: students cannot probe drafts or closed jobs.
    if job is None or job.status != JobStatus.OPEN:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found.")

    result = check_eligibility(student_snapshot(student), job_snapshot(job), today)
    return EligibilityOut(
        job=JobRef(id=job.id, title=job.title, company=job.company.name),
        **{k: getattr(result, k) for k in result.__dataclass_fields__},
    )
