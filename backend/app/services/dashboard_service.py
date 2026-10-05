"""The student dashboard: one read-only summary composed from the existing modules.

Nothing here re-implements a rule. Profile completeness, recommendations, eligibility, applications,
interviews and the resume come from the same services the individual pages use, so the dashboard and
those pages can never disagree. Every figure is computed from the database on each request.

Each section is built independently: if one fails, the rest still load and the failed one is reported
in `errors` (the page shows an error with a retry just for that widget).
"""
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import ApplicationStatus, Skill, Student, User
from app.repositories import job_repository, resume_repository
from app.schemas.dashboard import (
    ApplicationItem,
    ApplicationsSection,
    ClosestJob,
    DashboardOut,
    DemandSkill,
    FunnelStep,
    InterviewItem,
    InterviewsSection,
    JobCard,
    Milestone,
    MissingSkill,
    NextStep,
    OpportunitiesSection,
    ProfileSection,
    ProgressSection,
    RecommendationsSection,
    ResumeSection,
    SkillGapsSection,
    StatisticsSection,
    StudentCard,
)
from app.services import application_service, profile_service, recommendation_service

logger = logging.getLogger("placegenie.dashboard")

PROFILE_READY_PERCENT = 80  # a profile this complete counts as "ready" for the progress tracker
CLOSING_SOON_DAYS = 7
# Skill gaps are summarised over jobs that actually fit the student: the best matches scoring at least
# MIN_RELEVANT_SCORE (up to MAX_GAP_JOBS), but never fewer than MIN_GAP_JOBS so a new profile still gets an answer.
MIN_RELEVANT_SCORE = 30
MAX_GAP_JOBS = 10
MIN_GAP_JOBS = 3
SECTION_ERROR = "This section could not be loaded right now."
FUNNEL_ORDER = ["applied", "shortlisted", "online_assessment", "technical_interview", "hr_interview", "selected", "rejected"]
PROGRESSED = {"shortlisted", "online_assessment", "technical_interview", "hr_interview", "selected"}


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


class _Context:
    """The data several sections share, each loaded at most once (and only if a section asks for it)."""

    def __init__(self, db: Session, user: User, student: Student, today: date):
        self.db, self.user, self.student, self.today = db, user, student, today
        self._cache: dict[str, object] = {}

    def _once(self, key, loader):
        if key not in self._cache:
            try:
                self._cache[key] = ("ok", loader())
            except SQLAlchemyError:
                raise  # a database failure is reported as such by the API
            except Exception as exc:  # noqa: BLE001 - remembered so dependants fail fast instead of recomputing
                self._cache[key] = ("error", exc)
        state, value = self._cache[key]
        if state == "error":
            raise value
        return value

    @property
    def recs(self):  # every open job, scored for this student, best first
        return self._once("recs", lambda: recommendation_service.recommend_for(self.db, self.user, limit=1000, today=self.today))

    @property
    def apps(self):
        return self._once("apps", lambda: application_service.list_mine(self.db, self.user, None, None))

    @property
    def interviews(self):
        def load():
            result = application_service.list_interviews(self.db, self.user, "all")
            return [i for i in result.items if i.application.status != ApplicationStatus.WITHDRAWN]

        return self._once("interviews", load)

    @property
    def applied_job_ids(self) -> set[int]:
        return {a.job.id for a in self.apps.items if a.status != ApplicationStatus.WITHDRAWN}

    @property
    def resume(self):
        return self._once("resume", lambda: resume_repository.get_current(self.db, self.student.id))


def _job_card(item, applied: set[int]) -> JobCard:
    return JobCard(
        job_id=item.job.id, title=item.job.title, company=item.job.company.name, location=item.job.location,
        deadline=item.job.deadline, match_score=item.match_score, eligibility=item.eligibility.result,
        missing_skills=item.missing_skills, already_applied=item.job.id in applied,
    )


# ---------------------------------------------------------------- sections
def _profile(ctx: _Context) -> ProfileSection:
    s = ctx.student
    c = profile_service.compute_completeness(s)
    return ProfileSection(score=c.score, missing=c.missing, skills=len(s.skills), projects=len(s.projects), certifications=len(s.certifications))


def _resume(ctx: _Context) -> ResumeSection:
    r = ctx.resume
    if r is None:
        return ResumeSection(uploaded=False)
    a = r.analysis
    return ResumeSection(
        uploaded=True, filename=r.original_name, uploaded_at=r.uploaded_at,
        completeness_score=a.completeness_score if a else None,
        skills_detected=len(a.detected_skills) if a else None,
        top_suggestions=[s["text"] for s in (a.suggestions or [])[:3]] if a else [],
    )


def _recommendations(ctx: _Context) -> RecommendationsSection:
    page, applied = ctx.recs, ctx.applied_job_ids
    return RecommendationsSection(
        open_jobs=page.total, eligible=page.counts.eligible, incomplete_profile=page.counts.incomplete_profile,
        not_eligible=page.counts.not_eligible, top=[_job_card(i, applied) for i in page.items[:5]], hints=page.profile_hints,
    )


def _opportunities(ctx: _Context) -> OpportunitiesSection:
    page, applied = ctx.recs, ctx.applied_job_ids
    eligible = [i for i in page.items if i.eligibility.eligible and i.job.id not in applied]
    horizon = ctx.today + timedelta(days=CLOSING_SOON_DAYS)
    closing = [
        i for i in page.items
        if i.job.deadline and ctx.today <= i.job.deadline <= horizon and i.eligibility.result != "NOT_ELIGIBLE" and i.job.id not in applied
    ]
    closing.sort(key=lambda i: (i.job.deadline, -i.match_score, i.job.id))
    return OpportunitiesSection(
        eligible_count=page.counts.eligible,
        eligible_percent=round(100 * page.counts.eligible / page.total) if page.total else 0,
        items=[_job_card(i, applied) for i in eligible[:5]],
        closing_soon=[_job_card(i, applied) for i in closing[:3]],
    )


def _applications(ctx: _Context) -> ApplicationsSection:
    apps = ctx.apps
    withdrawn = apps.counts.get("withdrawn", 0)
    return ApplicationsSection(
        total=len(apps.items), active=len(apps.items) - withdrawn, by_status=apps.counts,
        recent=[
            ApplicationItem(id=a.id, job_title=a.job.title, company=a.job.company, status=a.status, applied_at=a.applied_at, next_interview=a.next_interview)
            for a in apps.items[:5]
        ],
    )


def _interviews(ctx: _Context) -> InterviewsSection:
    items = ctx.interviews
    upcoming = [i for i in items if i.is_upcoming]
    outcome = lambda name: sum(1 for i in items if i.outcome.value == name)  # noqa: E731
    return InterviewsSection(
        upcoming=[
            InterviewItem(id=i.id, application_id=i.application.id, stage=i.stage.value, scheduled_at=i.scheduled_at,
                          job_title=i.application.job.title, company=i.application.job.company)
            for i in upcoming[:5]
        ],
        upcoming_count=len(upcoming),
        needs_result=sum(1 for i in items if i.needs_result),
        total=len(items), passed=outcome("passed"), not_cleared=outcome("failed"), pending=outcome("pending"),
    )


def _skill_gaps(ctx: _Context) -> SkillGapsSection:
    has_skills = bool(ctx.student.skills)
    if not has_skills:  # without skills every job looks equally "missing everything", which says nothing useful
        return SkillGapsSection(student_has_skills=False, based_on_jobs=0, top_missing=[], closest_job=None)
    ranked_jobs = ctx.recs.items  # best match first
    relevant = [i for i in ranked_jobs if i.match_score >= MIN_RELEVANT_SCORE][:MAX_GAP_JOBS]
    focus = relevant if len(relevant) >= MIN_GAP_JOBS else ranked_jobs[:MIN_GAP_JOBS]
    needed: dict[str, list[str]] = defaultdict(list)
    for item in focus:
        for name in item.missing_skills:
            needed[name].append(item.job.title)
    ranked = sorted(needed.items(), key=lambda kv: (-len(kv[1]), kv[0].lower()))[:6]
    closest = next(
        (i for i in focus if i.eligibility.result == "NOT_ELIGIBLE" and set(i.eligibility.failed_requirements) == {"Required skills"} and 1 <= len(i.missing_skills) <= 3),
        None,
    )
    return SkillGapsSection(
        student_has_skills=True, based_on_jobs=len(focus),
        top_missing=[MissingSkill(name=n, jobs_needing=len(j), example_jobs=j[:2]) for n, j in ranked],
        closest_job=ClosestJob(job_id=closest.job.id, title=closest.job.title, company=closest.job.company.name,
                               match_score=closest.match_score, missing_skills=closest.missing_skills) if closest else None,
    )


def _statistics(ctx: _Context) -> StatisticsSection:
    page = ctx.recs
    horizon = ctx.today + timedelta(days=CLOSING_SOON_DAYS)
    demand, _ = job_repository.skill_demand(ctx.db)
    top = sorted(demand.items(), key=lambda kv: -kv[1])
    names = {sid: name for sid, name in ctx.db.execute(select(Skill.id, Skill.name).where(Skill.id.in_([sid for sid, _ in top[:30]])))} if top else {}
    mine = {s.skill_id for s in ctx.student.skills}
    in_demand = sorted(
        (DemandSkill(name=names[sid], jobs=n, you_have=sid in mine) for sid, n in top[:30] if sid in names),
        key=lambda d: (-d.jobs, d.name.lower()),
    )[:8]
    by_status = ctx.apps.counts
    decided = [i for i in ctx.interviews if i.outcome.value in ("passed", "failed")]
    passed = sum(1 for i in decided if i.outcome.value == "passed")
    return StatisticsSection(
        open_jobs=page.total,
        companies_hiring=len({i.job.company.id for i in page.items}),
        closing_this_week=sum(1 for i in page.items if i.job.deadline and ctx.today <= i.job.deadline <= horizon),
        eligible_percent=round(100 * page.counts.eligible / page.total) if page.total else 0,
        in_demand_skills=in_demand,
        application_funnel=[FunnelStep(status=s, count=by_status.get(s, 0)) for s in FUNNEL_ORDER],
        interview_pass_rate=round(100 * passed / len(decided)) if decided else None,
    )


def _progress(ctx: _Context) -> ProgressSection:
    profile = profile_service.compute_completeness(ctx.student)
    resume = ctx.resume
    counts = ctx.apps.counts
    active = sum(n for s, n in counts.items() if s != "withdrawn")
    progressed = sum(n for s, n in counts.items() if s in PROGRESSED)
    interviews = len(ctx.interviews)
    selected = counts.get("selected", 0)
    milestones = [
        Milestone(key="profile", label="Complete your profile", done=profile.score >= PROFILE_READY_PERCENT,
                  detail=f"{profile.score}% complete", link="/student/profile"),
        Milestone(key="resume", label="Upload your resume", done=resume is not None,
                  detail="Uploaded" if resume else "Not uploaded yet", link="/student/resume"),
        Milestone(key="applied", label="Apply to a job", done=active > 0,
                  detail=f"{active} application{'s' if active != 1 else ''}" if active else "No applications yet", link="/student/recommendations"),
        Milestone(key="progressed", label="Get shortlisted", done=progressed > 0,
                  detail=f"{progressed} moved forward" if progressed else "Waiting on the placement cell", link="/student/applications"),
        Milestone(key="interviewed", label="Record an interview", done=interviews > 0,
                  detail=f"{interviews} recorded" if interviews else "None recorded yet", link="/student/interviews"),
        Milestone(key="selected", label="Receive an offer", done=selected > 0,
                  detail="Selected" if selected else "Not yet", link="/student/applications"),
    ]
    reasons = {
        "profile": "Eligibility and recommendations are only as good as your profile.",
        "resume": "A resume lets PlaceGenie suggest improvements and match you to jobs.",
        "applied": "Pick a job that suits you and apply.",
        "progressed": "Check your applications for updates from the placement cell.",
        "interviewed": "Keep dates and notes for every round in one place.",
    }
    first_open = next((m for m in milestones if not m.done and m.key != "selected"), None)
    done = sum(m.done for m in milestones)
    return ProgressSection(
        percent=round(100 * done / len(milestones)), done=done, total=len(milestones), milestones=milestones,
        next_step=NextStep(key=first_open.key, label=first_open.label, reason=reasons[first_open.key], link=first_open.link) if first_open else None,
    )


# ---------------------------------------------------------------- entry point
SECTIONS = {
    "profile": _profile,
    "resume": _resume,
    "recommendations": _recommendations,
    "opportunities": _opportunities,
    "applications": _applications,
    "interviews": _interviews,
    "skill_gaps": _skill_gaps,
    "progress": _progress,
    "statistics": _statistics,
}


def build_dashboard(db: Session, user: User, today: date | None = None, only: set[str] | None = None) -> DashboardOut:
    """`only` limits the work to some sections (a coordinator viewing one student does not need the rest)."""
    student = profile_service.get_student(db, user)
    ctx = _Context(db, user, student, today or date.today())

    results: dict[str, object] = {}
    errors: dict[str, str] = {}
    for name, builder in SECTIONS.items():
        if only is not None and name not in only:
            results[name] = None  # not requested: neither built nor reported as an error
            continue
        try:
            results[name] = builder(ctx)
        except SQLAlchemyError:
            raise
        except Exception:  # noqa: BLE001 - one broken section must not blank the whole dashboard
            logger.exception("Dashboard section %r failed", name)
            results[name] = None
            errors[name] = SECTION_ERROR

    full_name = user.full_name or student.full_name
    return DashboardOut(
        generated_at=_now(),
        student=StudentCard(
            name=full_name, first_name=full_name.split()[0] if full_name.split() else full_name,
            branch=student.branch.name if student.branch else None, year=student.year, semester=student.semester,
            cgpa=float(student.cgpa) if student.cgpa is not None else None,
        ),
        errors=errors,
        **results,
    )
