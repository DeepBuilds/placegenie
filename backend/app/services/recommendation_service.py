"""Builds the inputs for the recommender from the database and shapes its output for the API."""
from datetime import date

from sqlalchemy.orm import Session

from app.ai.recommender import (
    RuleBasedRecommender,
    JobProfile,
    Recommendation,
    StudentProfile,
    build_job_text,
    default_recommender,
    student_hints,
)
from app.models import Job, JobStatus, Student, User
from app.repositories import job_repository
from app.schemas.recommendation import (
    ComponentOut,
    EligibilityCounts,
    RecEligibility,
    RecommendationOut,
    RecommendationPage,
)
from app.services import eligibility_service, job_service, profile_service

CANDIDATE_LIMIT = 1000  # demo scale: score every matching open job, then paginate in memory


def latest_resume_text(student: Student) -> str:
    """Text of the student's newest active resume (empty until resumes exist, Phase 8)."""
    resumes = [r for r in student.resumes if r.is_active and r.extracted_text]
    return max(resumes, key=lambda r: r.id).extracted_text if resumes else ""


def build_student_profile(student: Student) -> StudentProfile:
    parts = [student.interests or ""]
    for p in student.projects:
        parts += [p.title, p.description or "", p.tech_stack or ""]
    for e in student.experiences:
        parts += [e.role, e.organization, e.description or ""]
    parts += [c.name for c in student.certifications]
    return StudentProfile(
        eligibility=eligibility_service.student_snapshot(student),
        interest_text=" ".join(p for p in parts if p).strip(),
        preferred_role_ids={r.id for r in student.preferred_roles},
        preferred_role_categories={r.category for r in student.preferred_roles if r.category},
        resume_text=latest_resume_text(student),
    )


def build_job_profile(job: Job) -> JobProfile:
    return JobProfile(
        job_id=job.id,
        eligibility=eligibility_service.job_snapshot(job),
        role_id=job.role_id,
        role_name=job.role.name if job.role else None,
        role_category=job.role.category if job.role else None,
        text=build_job_text(
            job.title,
            job.role.name if job.role else None,
            job.description,
            job.company.industry,
            [js.skill.name for js in job.skills],
        ),
    )


def _to_out(job: Job, rec: Recommendation) -> RecommendationOut:
    e = rec.eligibility
    return RecommendationOut(
        job=job_service.to_job_out(job),
        match_score=rec.score,
        eligibility=RecEligibility(
            result=e.result,
            eligible=e.eligible,
            multiplier=rec.eligibility_multiplier,
            failed_requirements=e.failed_requirements,
            incomplete_fields=e.incomplete_fields,
        ),
        matched_skills=rec.matched_skills,
        missing_skills=rec.missing_skills,
        missing_preferred_skills=rec.missing_preferred_skills,
        reasons=rec.reasons,
        concerns=rec.concerns,
        breakdown=[
            ComponentOut(
                key=c.key, label=c.label, available=c.available, weight=round(c.weight, 4),
                score=round(c.score, 4), points=round(c.points, 2), note=c.note,
            )
            for c in rec.breakdown
        ],
    )


SORTS = {
    "score_desc": lambda r: (-r.match_score, r.job.deadline is None, r.job.deadline or date.max, r.job.id),
    "score_asc": lambda r: (r.match_score, r.job.id),
    "deadline": lambda r: (r.job.deadline is None, r.job.deadline or date.max, -r.match_score, r.job.id),
    "title": lambda r: (r.job.title.lower(), r.job.id),
}


def recommend_for(
    db: Session,
    user: User,
    *,
    role_id: int | None = None,
    location: str | None = None,
    eligible_only: bool = False,
    sort: str = "score_desc",
    limit: int = 10,
    offset: int = 0,
    today: date | None = None,
) -> RecommendationPage:
    student = profile_service.get_student(db, user)
    profile = build_student_profile(student)

    # Candidates: open jobs whose deadline has not passed, narrowed by the optional filters.
    filters = job_repository.JobFilters(
        status=JobStatus.OPEN, hide_expired=True, role_id=role_id, location=location
    )
    jobs, _ = job_repository.search_jobs(db, filters, CANDIDATE_LIMIT, 0)
    by_id = {j.id: j for j in jobs}

    recs = default_recommender().recommend(profile, [build_job_profile(j) for j in jobs], today)
    outs = [_to_out(by_id[r.job_id], r) for r in recs]

    counts = EligibilityCounts(
        eligible=sum(o.eligibility.result == "ELIGIBLE" for o in outs),
        incomplete_profile=sum(o.eligibility.result == "INCOMPLETE_PROFILE" for o in outs),
        not_eligible=sum(o.eligibility.result == "NOT_ELIGIBLE" for o in outs),
    )
    if eligible_only:
        outs = [o for o in outs if o.eligibility.eligible]
    outs.sort(key=SORTS[sort])

    return RecommendationPage(
        items=outs[offset : offset + limit],
        total=len(outs),
        limit=limit,
        offset=offset,
        counts=counts,
        profile_hints=student_hints(profile),
    )
