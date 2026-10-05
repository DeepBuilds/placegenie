"""Rule-based eligibility engine: student profile VS job requirements.

Pure functions only (no database, no randomness, no ML), so every decision is
deterministic and explainable. Inputs are plain snapshots; the output lists each
criterion with the required value, the student's value and a readable message.

Criterion status:
  passed         the requirement is satisfied
  failed         the requirement is not satisfied
  not_evaluated  the profile has no data to judge it (e.g. CGPA not filled in)

Overall result:
  ELIGIBLE            every criterion passed
  NOT_ELIGIBLE        at least one criterion failed
  INCOMPLETE_PROFILE  nothing failed, but some criteria could not be evaluated
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

PASSED, FAILED, NOT_EVALUATED = "passed", "failed", "not_evaluated"
ELIGIBLE, NOT_ELIGIBLE, INCOMPLETE_PROFILE = "ELIGIBLE", "NOT_ELIGIBLE", "INCOMPLETE_PROFILE"


# ---------- inputs ----------
@dataclass
class ExperiencePeriod:
    start: date | None
    end: date | None  # None = ongoing


@dataclass
class StudentSnapshot:
    cgpa: float | None
    branch_id: int | None
    branch_name: str | None
    backlogs: int
    skill_ids: set[int]
    certifications: list[str]
    experiences: list[ExperiencePeriod] = field(default_factory=list)


@dataclass
class JobSkillReq:
    skill_id: int
    name: str
    required: bool


@dataclass
class JobSnapshot:
    is_open: bool
    deadline: date | None
    min_cgpa: float  # 0 = no minimum
    max_backlogs: int | None  # None = no limit
    min_experience_months: int  # 0 = none
    allowed_branches: dict[int, str]  # id -> name; empty = every branch allowed
    skills: list[JobSkillReq]
    required_certifications: list[str]


# ---------- output ----------
@dataclass
class Criterion:
    key: str
    label: str
    status: str
    required: str
    actual: str
    message: str


@dataclass
class EligibilityResult:
    result: str
    eligible: bool
    summary: str
    criteria: list[Criterion]
    failed_requirements: list[str]
    reasons: list[str]  # why the student is not (or cannot be shown to be) eligible
    missing_skills: list[str]  # required skills the student lacks
    missing_preferred_skills: list[str]  # nice-to-have skills the student lacks (never blocking)
    missing_certifications: list[str]
    incomplete_fields: list[str]  # profile fields to fill in so everything can be checked


# ---------- helpers ----------
def _fmt(n: float) -> str:
    return f"{n:.2f}"


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def total_experience_months(periods: list[ExperiencePeriod], today: date) -> int:
    """Whole months of experience, counting overlapping periods only once.

    Entries without a start date are ignored (nothing to measure). An empty end date
    means the experience is ongoing and counts up to `today`.
    """
    spans = []
    for p in periods:
        if p.start is None:
            continue
        end = p.end or today
        if end >= p.start:
            spans.append((p.start, min(end, today)))
    spans = [s for s in spans if s[1] >= s[0]]
    spans.sort()
    merged: list[list[date]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    days = sum((end - start).days for start, end in merged)
    return days // 30


# ---------- individual rules ----------
def check_cgpa(student: StudentSnapshot, job: JobSnapshot) -> Criterion:
    if job.min_cgpa <= 0:
        return Criterion("cgpa", "CGPA", PASSED, "No minimum", _fmt(student.cgpa) if student.cgpa is not None else "Not entered", "This job has no CGPA requirement.")
    required = f"{_fmt(job.min_cgpa)} or above"
    if student.cgpa is None:
        return Criterion("cgpa", "CGPA", NOT_EVALUATED, required, "Not entered", "Add your CGPA to your profile so this can be checked.")
    if student.cgpa >= job.min_cgpa:
        return Criterion("cgpa", "CGPA", PASSED, required, _fmt(student.cgpa), f"Your CGPA ({_fmt(student.cgpa)}) meets the minimum of {_fmt(job.min_cgpa)}.")
    return Criterion("cgpa", "CGPA", FAILED, required, _fmt(student.cgpa), f"Your CGPA ({_fmt(student.cgpa)}) is below the required {_fmt(job.min_cgpa)}.")


def check_branch(student: StudentSnapshot, job: JobSnapshot) -> Criterion:
    if not job.allowed_branches:
        return Criterion("branch", "Branch", PASSED, "All branches", student.branch_name or "Not entered", "This job is open to every branch.")
    allowed = sorted(job.allowed_branches.values(), key=str.lower)
    required = ", ".join(allowed)
    if student.branch_id is None:
        return Criterion("branch", "Branch", NOT_EVALUATED, required, "Not entered", "Select your branch in your profile so this can be checked.")
    if student.branch_id in job.allowed_branches:
        return Criterion("branch", "Branch", PASSED, required, student.branch_name or "", f"Your branch ({student.branch_name}) is allowed.")
    return Criterion("branch", "Branch", FAILED, required, student.branch_name or "", f"Your branch ({student.branch_name}) is not among the allowed branches.")


def check_backlogs(student: StudentSnapshot, job: JobSnapshot) -> Criterion:
    if job.max_backlogs is None:
        return Criterion("backlogs", "Backlogs", PASSED, "No limit", str(student.backlogs), "This job has no backlog restriction.")
    required = "No backlogs allowed" if job.max_backlogs == 0 else f"At most {job.max_backlogs}"
    if student.backlogs <= job.max_backlogs:
        return Criterion("backlogs", "Backlogs", PASSED, required, str(student.backlogs), f"Your backlogs ({student.backlogs}) are within the limit.")
    return Criterion("backlogs", "Backlogs", FAILED, required, str(student.backlogs), f"You have {_plural(student.backlogs, 'backlog')}, but the maximum allowed is {job.max_backlogs}.")


def check_skills(student: StudentSnapshot, job: JobSnapshot) -> tuple[Criterion, list[str], list[str]]:
    required = [s for s in job.skills if s.required]
    preferred = [s for s in job.skills if not s.required]
    missing = sorted((s.name for s in required if s.skill_id not in student.skill_ids), key=str.lower)
    missing_pref = sorted((s.name for s in preferred if s.skill_id not in student.skill_ids), key=str.lower)
    if not required:
        note = "This job lists no required skills."
        if preferred:
            note += f" You match {len(preferred) - len(missing_pref)}/{len(preferred)} preferred skills."
        return Criterion("skills", "Required skills", PASSED, "None", "-", note), missing, missing_pref

    matched = len(required) - len(missing)
    req_text = f"All {len(required)} required skills"
    actual = f"{matched}/{len(required)} matched"
    if not missing:
        msg = "You have all the required skills."
        if preferred:
            msg += f" Preferred skills matched: {len(preferred) - len(missing_pref)}/{len(preferred)}."
        return Criterion("skills", "Required skills", PASSED, req_text, actual, msg), missing, missing_pref
    return (
        Criterion("skills", "Required skills", FAILED, req_text, actual, f"Missing required skill(s): {', '.join(missing)}."),
        missing,
        missing_pref,
    )


def check_certifications(student: StudentSnapshot, job: JobSnapshot) -> tuple[Criterion, list[str]]:
    if not job.required_certifications:
        return Criterion("certifications", "Certifications", PASSED, "None required", "-", "This job does not require a certification."), []
    have = {_norm(c) for c in student.certifications}
    missing = sorted((c for c in job.required_certifications if _norm(c) not in have), key=str.lower)
    required = ", ".join(sorted(job.required_certifications, key=str.lower))
    matched = len(job.required_certifications) - len(missing)
    actual = f"{matched}/{len(job.required_certifications)} held"
    if not missing:
        return Criterion("certifications", "Certifications", PASSED, required, actual, "You hold all required certifications."), []
    return Criterion("certifications", "Certifications", FAILED, required, actual, f"Missing certification(s): {', '.join(missing)}."), missing


def check_experience(student: StudentSnapshot, job: JobSnapshot, today: date) -> Criterion:
    months = total_experience_months(student.experiences, today)
    if job.min_experience_months <= 0:
        return Criterion("experience", "Experience", PASSED, "Freshers welcome", _plural(months, "month"), "This job does not require prior experience.")
    required = _plural(job.min_experience_months, "month")
    if months >= job.min_experience_months:
        return Criterion("experience", "Experience", PASSED, required, _plural(months, "month"), f"Your experience ({_plural(months, 'month')}) meets the requirement.")
    return Criterion("experience", "Experience", FAILED, required, _plural(months, "month"), f"The job needs {required} of experience; your profile shows {_plural(months, 'month')}.")


def check_deadline(job: JobSnapshot, today: date) -> Criterion:
    if not job.is_open:
        return Criterion("deadline", "Application window", FAILED, "Job open for applications", "Closed", "This job is not open for applications.")
    if job.deadline is None:
        return Criterion("deadline", "Application window", PASSED, "No deadline", "Open", "This job has no application deadline.")
    required = f"Apply by {job.deadline.isoformat()}"
    if job.deadline < today:
        return Criterion("deadline", "Application window", FAILED, required, f"Closed on {job.deadline.isoformat()}", f"The application deadline ({job.deadline.isoformat()}) has passed.")
    days_left = (job.deadline - today).days
    when = "today" if days_left == 0 else f"in {_plural(days_left, 'day')}"
    return Criterion("deadline", "Application window", PASSED, required, "Open", f"Applications are open; the deadline is {when}.")


# ---------- orchestration ----------
def check_eligibility(student: StudentSnapshot, job: JobSnapshot, today: date | None = None) -> EligibilityResult:
    today = today or date.today()

    cgpa = check_cgpa(student, job)
    branch = check_branch(student, job)
    backlogs = check_backlogs(student, job)
    skills, missing_skills, missing_pref = check_skills(student, job)
    certs, missing_certs = check_certifications(student, job)
    experience = check_experience(student, job, today)
    deadline = check_deadline(job, today)
    criteria = [cgpa, branch, backlogs, skills, certs, experience, deadline]

    failed = [c for c in criteria if c.status == FAILED]
    unknown = [c for c in criteria if c.status == NOT_EVALUATED]

    if failed:
        result, eligible = NOT_ELIGIBLE, False
        summary = f"You are not eligible: {_plural(len(failed), 'requirement')} not met."
    elif unknown:
        result, eligible = INCOMPLETE_PROFILE, False
        summary = "Eligibility could not be fully checked because your profile is incomplete."
    else:
        result, eligible = ELIGIBLE, True
        summary = "You meet all the listed requirements for this job."

    incomplete = [{"cgpa": "CGPA", "branch": "Branch"}[c.key] for c in unknown]
    reasons = [c.message for c in failed] + [c.message for c in unknown]

    return EligibilityResult(
        result=result,
        eligible=eligible,
        summary=summary,
        criteria=criteria,
        failed_requirements=[c.label for c in failed],
        reasons=reasons,
        missing_skills=missing_skills,
        missing_preferred_skills=missing_pref,
        missing_certifications=missing_certs,
        incomplete_fields=incomplete,
    )
