"""Reports for the student and for the placement cell.

Every figure comes from a service that already exists, so a report can never disagree with a page:
  * the student's report    -> the student dashboard's sections and the application/interview lists
  * the coordinator report  -> coordinator_service (one cohort snapshot, loaded once)
Only the totals and the job-wise table are new here.
"""
from collections import Counter, defaultdict
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import ApplicationStatus, Job, User
from app.schemas.coordinator import StatusCount
from app.schemas.report import (
    ApplicationSummary,
    CoordinatorReport,
    InterviewReport,
    JobStats,
    PlacementStats,
    ReportApplication,
    ReportInterview,
    SelectedStudent,
    SkillGap,
    StudentReport,
)
from app.services import coordinator_service as cs
from app.services import dashboard_service

TOP_SKILL_GAPS = 10


# =====================================================================
# Student report
# =====================================================================
def student_report(db: Session, user: User, today: date | None = None, light: bool = False) -> StudentReport:
    """`light` skips the recommendation, skill-gap and progress sections (the CSV export does not show them)."""
    ctx = dashboard_service.new_context(db, user, today)
    dash = dashboard_service.build_dashboard(db, user, only=set() if light else {"recommendations", "skill_gaps", "progress"}, ctx=ctx)

    apps = ctx.apps  # all of the student's applications, newest first (loaded once, shared with the sections above)
    counts = apps.counts
    active = sum(n for s, n in counts.items() if s != "withdrawn")
    in_process = sum(n for s, n in counts.items() if s in cs.IN_PROCESS)
    overall = cs.stage_of([s for s, n in counts.items() for _ in range(n)])

    interviews = ctx.interviews  # of applications that are not withdrawn
    passed = sum(1 for i in interviews if i.outcome.value == "passed")
    failed = sum(1 for i in interviews if i.outcome.value == "failed")
    decided = passed + failed

    return StudentReport(
        generated_at=datetime.now().replace(microsecond=0),
        student=dash.student,
        summary=ApplicationSummary(
            total=len(apps.items), active=active, awaiting_review=counts.get("applied", 0), in_process=in_process,
            selected=counts.get("selected", 0), rejected=counts.get("rejected", 0), withdrawn=counts.get("withdrawn", 0),
            outcome=overall, outcome_label=cs.STAGE_LABELS[overall],
        ),
        status_distribution=[StatusCount(status=s, count=counts.get(s, 0)) for s in cs.STATUS_ORDER],
        applications=[
            ReportApplication(
                id=a.id, job_id=a.job.id, job_title=a.job.title, company=a.job.company, status=a.status.value,
                applied_at=a.applied_at, updated_at=a.updated_at, interviews=a.interview_count, next_interview=a.next_interview,
            )
            for a in apps.items
        ],
        interviews=InterviewReport(
            total=len(interviews), passed=passed, not_cleared=failed, pending=sum(1 for i in interviews if i.outcome.value == "pending"),
            upcoming=sum(1 for i in interviews if i.is_upcoming), pass_rate=round(100 * passed / decided) if decided else None,
            items=[
                ReportInterview(id=i.id, application_id=i.application.id, job_title=i.application.job.title, company=i.application.job.company,
                                stage=i.stage.value, scheduled_at=i.scheduled_at, outcome=i.outcome.value)
                for i in interviews
            ],
        ),
        recommended=dash.recommendations, skill_gaps=dash.skill_gaps, progress=dash.progress, errors=dash.errors,
    )


# =====================================================================
# Coordinator report
# =====================================================================
def job_stats(db: Session, c: cs.Cohort) -> list[JobStats]:
    """One row per job (also jobs nobody applied to), busiest first. Counts every application record."""
    per_job: dict[int, Counter] = defaultdict(Counter)
    for a in c.applications:
        per_job[a.job_id][a.status.value] += 1
    jobs = db.scalars(select(Job).options(selectinload(Job.company)))
    rows = []
    for j in jobs:
        n = per_job.get(j.id, Counter())
        rows.append(JobStats(
            job_id=j.id, title=j.title, company=j.company.name, status=j.status.value, deadline=j.deadline,
            applications=sum(n.values()), awaiting_review=n["applied"], in_process=sum(n[s] for s in cs.IN_PROCESS),
            selected=n["selected"], rejected=n["rejected"], withdrawn=n["withdrawn"],
        ))
    return sorted(rows, key=lambda r: (-r.applications, r.title.lower(), r.job_id))


def selected_students(c: cs.Cohort) -> list[SelectedStudent]:
    """One row per selected application (a student selected twice appears twice), newest decision first."""
    by_id = {s.id: s for s in c.students}
    rows = []
    for a in c.applications:
        if a.status != ApplicationStatus.SELECTED:
            continue
        s = by_id[a.student_id]
        rows.append(SelectedStudent(
            student_id=s.id, name=s.full_name, email=s.user.email, branch=s.branch.name if s.branch else None,
            cgpa=float(s.cgpa) if s.cgpa is not None else None, company=a.job.company.name, job_title=a.job.title, selected_on=a.updated_at.date(),
        ))
    return sorted(rows, key=lambda r: (r.selected_on, r.student_id), reverse=True)


def skill_gaps(db: Session, c: cs.Cohort) -> list[SkillGap]:
    """Skills that open jobs ask for and many students do not have: most-requested first."""
    total = len(c.students)
    rows = [
        SkillGap(skill=r.skill, jobs_requiring=r.jobs_requiring, students_with=r.students_with,
                 students_lacking=total - r.students_with, percent_lacking=round(100 * (total - r.students_with) / total) if total else 0)
        for r in cs.skill_supply(db, c, limit=None) if total - r.students_with > 0
    ]
    rows.sort(key=lambda r: (-r.jobs_requiring, -r.students_lacking, r.skill.lower()))
    return rows[:TOP_SKILL_GAPS]


def coordinator_report(db: Session) -> CoordinatorReport:
    c = cs.load_cohort(db)  # the one snapshot every figure below is counted from
    progress = cs.build_progress(db, c)
    stages = Counter(c.stage(s.id) for s in c.students)
    counts = Counter(a.status.value for a in c.applications)
    by_branch, by_cgpa = cs.students_by_branch_and_cgpa(c)
    placed = stages["placed"]

    return CoordinatorReport(
        generated_at=datetime.now().replace(microsecond=0),
        placement=PlacementStats(
            total_students=len(c.students), applicants=len(c.students) - stages["not_applied"], placed=placed,
            in_process=stages["in_process"], rejected=stages["rejected"], not_applied=stages["not_applied"],
            placement_rate=cs.placement_rate(placed, len(c.students)), by_stage=progress.current_stage, by_branch=by_branch, by_cgpa=by_cgpa,
        ),
        status_distribution=[StatusCount(status=s, count=counts.get(s, 0)) for s in cs.STATUS_ORDER],
        companies=cs.company_stats(db, c), jobs=job_stats(db, c), selected_students=selected_students(c),
        skill_gaps=skill_gaps(db, c), interviews=cs.interview_outcomes(c), progress=progress, min_group_size=cs.MIN_STUDENTS_FOR_RATE,
    )
