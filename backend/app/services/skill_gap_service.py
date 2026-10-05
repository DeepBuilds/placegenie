"""Loads the student, the job and the market demand, then runs the pure skill-gap rules."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.skill_gap import JobSkillInfo, analyze_skill_gap
from app.models import JobStatus, SkillImportance, User
from app.repositories import job_repository
from app.schemas.eligibility import JobRef
from app.schemas.skill_gap import SkillGapOut
from app.services import profile_service

DISCLAIMER = (
    "Priorities come from this job's requirements and how often skills appear in the currently open jobs. "
    "They are guidance only: they do not predict hiring decisions or how long a skill takes to learn."
)


def analyze_for_student(db: Session, user: User, job_id: int) -> SkillGapOut:
    student = profile_service.get_student(db, user)
    job = job_repository.get_job(db, job_id)
    # Same visibility rule as the job pages: students cannot probe drafts or closed jobs.
    if job is None or job.status != JobStatus.OPEN:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found.")

    job_skills = [
        JobSkillInfo(js.skill_id, js.skill.name, js.skill.category, js.importance == SkillImportance.REQUIRED, js.weight)
        for js in job.skills
    ]
    levels = {s.skill_id: s.proficiency.value for s in student.skills}
    demand, total_open = job_repository.skill_demand(db)

    result = analyze_skill_gap(job_skills, levels, demand, total_open)
    return SkillGapOut(
        job=JobRef(id=job.id, title=job.title, company=job.company.name),
        open_jobs_compared=total_open,
        disclaimer=DISCLAIMER,
        **{k: getattr(result, k) for k in result.__dataclass_fields__},
    )
