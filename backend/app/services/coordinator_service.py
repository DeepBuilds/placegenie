"""The coordinator's view of the whole cohort: statistics, students, progress and analytics.

Nothing here re-implements a rule from another module:
  * profile completeness      -> profile_service.compute_completeness
  * the "profile ready" bar and the in-progress statuses -> constants from dashboard_service
  * one student's placement profile -> the same services (and the student dashboard builder) the student's own pages use
  * skill demand              -> job_repository.skill_demand
The cohort is loaded once per request and summarised in Python, which is plenty for a college-sized cohort.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Application,
    ApplicationStatus,
    Company,
    InterviewStage,
    Job,
    JobStatus,
    Resume,
    Skill,
    Student,
    StudentSkill,
)
from app.repositories import job_repository
from app.schemas.coordinator import (
    Analytics,
    Attention,
    BranchRef,
    BranchStats,
    CgpaBand,
    ClosingJob,
    CohortProgress,
    CompanyStats,
    CoordinatorDashboard,
    CoordinatorStats,
    InterviewOutcomes,
    PlacementRate,
    RecentApplication,
    SkillSupply,
    StageStep,
    StatusCount,
    StudentDetail,
    StudentPage,
    StudentRow,
)
from app.services import application_service, dashboard_service, profile_service

MIN_STUDENTS_FOR_RATE = 5  # a placement rate over fewer students says nothing
CLOSING_SOON_DAYS = 7
IN_PROCESS = {"shortlisted", "online_assessment", "technical_interview", "hr_interview"}  # being considered, no decision yet
STATUS_ORDER = ["applied", "shortlisted", "online_assessment", "technical_interview", "hr_interview", "selected", "rejected", "withdrawn"]
STAGES = [("placed", "Placed"), ("in_process", "In the selection process"), ("applied", "Applied, awaiting review"),
          ("rejected", "Not selected so far"), ("not_applied", "Not applied yet")]
STAGE_LABELS = dict(STAGES)
CGPA_BANDS = [("Below 6.0", 0, 6), ("6.0 - 6.9", 6, 7), ("7.0 - 7.9", 7, 8), ("8.0 - 8.9", 8, 9), ("9.0 and above", 9, 10.01)]


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


def stage_of(statuses: list[str]) -> str:
    """Where a student stands, from the statuses of their applications."""
    active = [s for s in statuses if s != "withdrawn"]
    if "selected" in active:
        return "placed"
    if any(s in IN_PROCESS for s in active):
        return "in_process"
    if any(s == "applied" for s in active):
        return "applied"
    if active:  # every remaining application was rejected
        return "rejected"
    return "not_applied"


# =====================================================================
# One consistent snapshot of the cohort
# =====================================================================
@dataclass
class Cohort:
    students: list[Student]
    applications: list[Application]
    resume_students: set[int]
    interviews: list[InterviewStage] = field(default_factory=list)  # of applications that are not withdrawn
    by_student: dict[int, list[Application]] = field(default_factory=lambda: defaultdict(list))

    def statuses(self, student_id: int) -> list[str]:
        return [a.status.value for a in self.by_student.get(student_id, [])]

    def stage(self, student_id: int) -> str:
        return stage_of(self.statuses(student_id))

    @property
    def interview_students(self) -> set[int]:
        return {i.application.student_id for i in self.interviews}


def load_cohort(db: Session) -> Cohort:
    students = list(db.scalars(
        select(Student).options(
            selectinload(Student.user), selectinload(Student.branch), selectinload(Student.skills),
            selectinload(Student.projects), selectinload(Student.preferred_roles),
        ).order_by(Student.id)
    ))
    applications = list(db.scalars(
        select(Application).options(selectinload(Application.job).selectinload(Job.company)).order_by(Application.id)
    ))
    interviews = list(db.scalars(
        select(InterviewStage).join(Application, Application.id == InterviewStage.application_id)
        .where(Application.status != ApplicationStatus.WITHDRAWN).options(selectinload(InterviewStage.application))
    ))
    cohort = Cohort(
        students=students, applications=applications, interviews=interviews,
        resume_students=set(db.scalars(select(Resume.student_id).where(Resume.is_active.is_(True)))),
    )
    for a in applications:
        cohort.by_student[a.student_id].append(a)
    return cohort


def _count(db: Session, model, *where) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*where)) or 0


def _rate(part: int, whole: int, minimum: int = MIN_STUDENTS_FOR_RATE) -> int | None:
    return round(100 * part / whole) if whole >= minimum else None


# =====================================================================
# Dashboard
# =====================================================================
def placement_rate(placed: int, total: int) -> PlacementRate:
    sufficient = total >= MIN_STUDENTS_FOR_RATE
    return PlacementRate(
        percent=round(100 * placed / total) if sufficient else None, placed=placed, total_students=total, sufficient_data=sufficient,
        note=f"{placed} of {total} registered students have a selected application." if sufficient
        else f"Needs at least {MIN_STUDENTS_FOR_RATE} registered students before a rate is meaningful (there are {total}).",
    )


def build_dashboard(db: Session, today: date | None = None) -> CoordinatorDashboard:
    today = today or date.today()
    c = load_cohort(db)
    active = [a for a in c.applications if a.status.value != "withdrawn"]
    statuses_by_student = {sid: c.statuses(sid) for sid in c.by_student}
    placed = sum(1 for s in statuses_by_student.values() if "selected" in s)
    in_process_students = sum(1 for s in statuses_by_student.values() if any(x in IN_PROCESS for x in s))
    counts = Counter(a.status.value for a in c.applications)

    stats = CoordinatorStats(
        total_students=len(c.students), total_companies=_count(db, Company), total_jobs=_count(db, Job),
        open_jobs=_count(db, Job, Job.status == JobStatus.OPEN), total_applications=len(c.applications),
        withdrawn_applications=counts.get("withdrawn", 0), applicants=len({a.student_id for a in active}),
        shortlisted_students=in_process_students, selected_students=placed, rejected_applications=counts.get("rejected", 0),
        placement_rate=placement_rate(placed, len(c.students)),
    )

    names = {s.id: s.full_name for s in c.students}
    recent = sorted(c.applications, key=lambda a: (a.applied_at, a.id), reverse=True)[:5]

    per_job = Counter(a.job_id for a in active)
    horizon = today + timedelta(days=CLOSING_SOON_DAYS)
    open_jobs = list(db.scalars(select(Job).where(Job.status == JobStatus.OPEN).options(selectinload(Job.company))))
    live_jobs = [j for j in open_jobs if not j.deadline or j.deadline >= today]
    closing = sorted((j for j in live_jobs if j.deadline and j.deadline <= horizon), key=lambda j: (j.deadline, j.id))[:5]
    now = _now()
    this_week = sum(1 for i in c.interviews if i.scheduled_at and now <= i.scheduled_at <= now + timedelta(days=7))

    return CoordinatorDashboard(
        generated_at=now, stats=stats,
        application_funnel=[StatusCount(status=s, count=counts.get(s, 0)) for s in STATUS_ORDER],
        recent_applications=[
            RecentApplication(id=a.id, student_id=a.student_id, student_name=names.get(a.student_id, "Unknown"), job_title=a.job.title,
                              company=a.job.company.name, status=a.status.value, applied_at=a.applied_at)
            for a in recent
        ],
        attention=Attention(
            awaiting_review=counts.get("applied", 0),
            closing_soon=[ClosingJob(job_id=j.id, title=j.title, company=j.company.name, deadline=j.deadline, applications=per_job.get(j.id, 0)) for j in closing],
            open_jobs_without_applications=sum(1 for j in live_jobs if per_job.get(j.id, 0) == 0),
            interviews_this_week=this_week,
        ),
    )


# =====================================================================
# Students
# =====================================================================
def _row(c: Cohort, s: Student) -> StudentRow:
    return StudentRow(
        id=s.id, full_name=s.full_name, email=s.user.email, college=s.college,
        branch=BranchRef(id=s.branch.id, name=s.branch.name) if s.branch else None, year=s.year, semester=s.semester,
        cgpa=float(s.cgpa) if s.cgpa is not None else None, backlogs=s.backlogs,
        profile_percent=profile_service.compute_completeness(s).score, has_resume=s.id in c.resume_students,
        applications=sum(1 for a in c.by_student.get(s.id, []) if a.status.value != "withdrawn"), stage=c.stage(s.id),
    )


SORTS = {
    "name": lambda r: (r.full_name.lower(), r.id),
    "cgpa": lambda r: (-(r.cgpa if r.cgpa is not None else -1), r.full_name.lower()),
    "profile": lambda r: (-r.profile_percent, r.full_name.lower()),
    "applications": lambda r: (-r.applications, r.full_name.lower()),
    "newest": lambda r: -r.id,
}


def list_students(
    db: Session, *, q: str | None, branch_id: int | None, year: int | None, min_cgpa: float | None, stage: str | None,
    has_resume: bool | None, profile_ready: bool | None, sort: str, limit: int, offset: int,
) -> StudentPage:
    c = load_cohort(db)
    rows = [_row(c, s) for s in c.students]
    stage_counts = Counter(r.stage for r in rows)

    needle = (q or "").strip().lower()
    chosen = [
        r for r in rows
        if (not needle or needle in r.full_name.lower() or needle in r.email.lower() or needle in (r.college or "").lower())
        and (branch_id is None or (r.branch and r.branch.id == branch_id))
        and (year is None or r.year == year)
        and (min_cgpa is None or (r.cgpa is not None and r.cgpa >= min_cgpa))
        and (stage is None or r.stage == stage)
        and (has_resume is None or r.has_resume == has_resume)
        and (profile_ready is None or (r.profile_percent >= dashboard_service.PROFILE_READY_PERCENT) == profile_ready)
    ]
    chosen.sort(key=SORTS[sort])
    return StudentPage(items=chosen[offset: offset + limit], total=len(chosen), limit=limit, offset=offset,
                       stage_counts={key: stage_counts.get(key, 0) for key, _ in STAGES})


def student_detail(db: Session, student_id: int) -> StudentDetail:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found.")
    user = student.user
    # Everything below is what the student's own pages show, produced by the same services.
    dash = dashboard_service.build_dashboard(db, user, only={"resume", "progress", "skill_gaps"})
    apps = application_service.list_mine(db, user, None, None)
    return StudentDetail(
        student_id=student.id, stage=stage_of([st for st, n in apps.counts.items() for _ in range(n)]),
        profile=profile_service.to_profile_out(profile_service.get_student(db, user)),
        resume=dash.resume, progress=dash.progress, skill_gaps=dash.skill_gaps, applications=apps,
        interviews=application_service.list_interviews(db, user, "all"), errors=dash.errors,
    )


# =====================================================================
# Cohort progress
# =====================================================================
def build_progress(db: Session, c: Cohort | None = None) -> CohortProgress:
    c = c or load_cohort(db)
    total = len(c.students)
    pct = lambda n: round(100 * n / total) if total else 0  # noqa: E731
    ready = {s.id for s in c.students if profile_service.compute_completeness(s).score >= dashboard_service.PROFILE_READY_PERCENT}
    applied = {sid for sid, apps in c.by_student.items() if any(a.status.value != "withdrawn" for a in apps)}
    moved = {sid for sid, apps in c.by_student.items() if any(a.status.value in dashboard_service.PROGRESSED for a in apps)}
    selected = {sid for sid, apps in c.by_student.items() if any(a.status.value == "selected" for a in apps)}
    reached = [
        ("registered", "Registered", total), ("profile", "Profile ready", len(ready)), ("resume", "Resume uploaded", len(c.resume_students & {s.id for s in c.students})),
        ("applied", "Applied to a job", len(applied)), ("progressed", "Shortlisted or beyond", len(moved)),
        ("interviewed", "Interview recorded", len(c.interview_students)), ("selected", "Selected", len(selected)),
    ]
    stage_counts = Counter(c.stage(s.id) for s in c.students)
    return CohortProgress(
        total_students=total,
        funnel=[StageStep(key=k, label=label, count=n, percent=pct(n)) for k, label, n in reached],
        current_stage=[StageStep(key=k, label=label, count=stage_counts.get(k, 0), percent=pct(stage_counts.get(k, 0))) for k, label in STAGES],
        needs_attention={
            "no_resume": sum(1 for s in c.students if s.id not in c.resume_students),
            "profile_not_ready": sum(1 for s in c.students if s.id not in ready),
            "not_applied": stage_counts.get("not_applied", 0),
        },
    )


# =====================================================================
# Analytics
# =====================================================================
def skill_supply(db: Session, c: Cohort, limit: int | None = 12) -> list[SkillSupply]:
    demand, _ = job_repository.skill_demand(db)
    if not demand:
        return []
    names = dict(db.execute(select(Skill.id, Skill.name).where(Skill.id.in_(list(demand)))).all())
    have = Counter(sid for sid, in db.execute(select(StudentSkill.skill_id)))
    total = len(c.students)
    rows = [
        SkillSupply(skill=names[sid], jobs_requiring=n, students_with=have.get(sid, 0), students_percent=round(100 * have.get(sid, 0) / total) if total else 0)
        for sid, n in demand.items() if sid in names
    ]
    rows.sort(key=lambda r: (-r.jobs_requiring, r.skill.lower()))
    return rows[:limit] if limit else rows


def company_stats(db: Session, c: Cohort) -> list[CompanyStats]:
    jobs_per_company = dict(db.execute(select(Company.name, func.count(Job.id)).outerjoin(Job, Job.company_id == Company.id).group_by(Company.name)).all())
    by_company: dict[str, Counter] = defaultdict(Counter)
    for a in c.applications:
        counter = by_company[a.job.company.name]
        counter["applications"] += 1
        counter["shortlisted"] += a.status.value in IN_PROCESS
        counter["selected"] += a.status.value == "selected"
        counter["rejected"] += a.status.value == "rejected"
    rows = [
        CompanyStats(company=name, jobs=jobs, applications=by_company[name]["applications"], shortlisted=by_company[name]["shortlisted"],
                     selected=by_company[name]["selected"], rejected=by_company[name]["rejected"])
        for name, jobs in jobs_per_company.items()
    ]
    return sorted(rows, key=lambda r: (-r.applications, r.company.lower()))


def students_by_branch_and_cgpa(c: Cohort) -> tuple[list[BranchStats], list[CgpaBand]]:
    """Placement numbers per branch and per CGPA band (a rate is hidden for a group smaller than MIN_STUDENTS_FOR_RATE)."""

    def group(keyfn):
        groups: dict[str, list[Student]] = defaultdict(list)
        for s in c.students:
            groups[keyfn(s)].append(s)
        return groups

    def cohort_numbers(members):
        placed = sum(1 for s in members if c.stage(s.id) == "placed")
        applicants = sum(1 for s in members if c.stage(s.id) != "not_applied")
        return len(members), applicants, placed

    by_branch = []
    for name, members in sorted(group(lambda s: s.branch.name if s.branch else "Branch not set").items()):
        n, applicants, placed = cohort_numbers(members)
        by_branch.append(BranchStats(branch=name, students=n, applicants=applicants, placed=placed, placement_rate=_rate(placed, n)))

    def band_of(s: Student) -> str:
        if s.cgpa is None:
            return "CGPA not entered"
        return next(label for label, low, high in CGPA_BANDS if low <= float(s.cgpa) < high)

    bands = group(band_of)
    by_cgpa = []
    for label, _, _ in [*CGPA_BANDS, ("CGPA not entered", 0, 0)]:
        members = bands.get(label, [])
        if members:
            n, _, placed = cohort_numbers(members)
            by_cgpa.append(CgpaBand(band=label, students=n, placed=placed, placement_rate=_rate(placed, n)))
    return by_branch, by_cgpa


def interview_outcomes(c: Cohort) -> InterviewOutcomes:
    outcomes = Counter(i.outcome.value for i in c.interviews)
    decided = outcomes["passed"] + outcomes["failed"]
    return InterviewOutcomes(
        total=len(c.interviews), passed=outcomes["passed"], not_cleared=outcomes["failed"], pending=outcomes["pending"],
        pass_rate=round(100 * outcomes["passed"] / decided) if decided else None)


def build_analytics(db: Session) -> Analytics:
    c = load_cohort(db)
    counts = Counter(a.status.value for a in c.applications)
    by_branch, by_cgpa = students_by_branch_and_cgpa(c)
    return Analytics(
        status_funnel=[StatusCount(status=s, count=counts.get(s, 0)) for s in STATUS_ORDER],
        by_company=company_stats(db, c)[:10], by_branch=by_branch, by_cgpa=by_cgpa, skill_supply=skill_supply(db, c),
        interview_outcomes=interview_outcomes(c), min_group_size=MIN_STUDENTS_FOR_RATE,
    )
