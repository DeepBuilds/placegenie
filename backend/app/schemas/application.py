from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import ApplicationStatus, InterviewStageType, JobType, StageOutcome
from app.schemas.eligibility import CriterionOut
from app.schemas.ids import BodyId

MIN_YEAR, MAX_YEAR = 2000, 2100


# ---------- requests ----------
class ApplyRequest(BaseModel):
    job_id: BodyId


class StatusUpdate(BaseModel):
    status: ApplicationStatus


def _clean_notes(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return v or None


def _check_date(v: datetime | None) -> datetime | None:
    if v is not None:
        if not MIN_YEAR <= v.year <= MAX_YEAR:
            raise ValueError(f"Enter a date between {MIN_YEAR} and {MAX_YEAR}.")
        v = v.replace(tzinfo=None, microsecond=0)  # stored as the local date/time the student typed
    return v


class InterviewCreate(BaseModel):
    stage: InterviewStageType
    scheduled_at: datetime | None = None
    outcome: StageOutcome = StageOutcome.PENDING
    notes: str | None = Field(default=None, max_length=2000)

    _notes = field_validator("notes")(classmethod(lambda cls, v: _clean_notes(v)))
    _date = field_validator("scheduled_at")(classmethod(lambda cls, v: _check_date(v)))


class InterviewUpdate(BaseModel):
    """Partial update: only fields that are sent change. Send `scheduled_at: null` to clear the date."""

    stage: InterviewStageType | None = None
    scheduled_at: datetime | None = None
    outcome: StageOutcome | None = None
    notes: str | None = Field(default=None, max_length=2000)

    _notes = field_validator("notes")(classmethod(lambda cls, v: _clean_notes(v)))
    _date = field_validator("scheduled_at")(classmethod(lambda cls, v: _check_date(v)))


# ---------- responses ----------
class JobBrief(BaseModel):
    id: int
    title: str
    company: str
    location: str | None
    job_type: JobType
    deadline: date | None
    is_expired: bool


class BranchBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class StudentBrief(BaseModel):
    id: int
    full_name: str
    email: str
    branch: BranchBrief | None
    cgpa: float | None


class InterviewOut(BaseModel):
    id: int
    application_id: int
    stage: InterviewStageType
    scheduled_at: datetime | None
    outcome: StageOutcome
    notes: str | None
    is_upcoming: bool  # scheduled in the future
    needs_result: bool  # the date has passed but no result was recorded
    created_at: datetime
    updated_at: datetime


class ApplicationBrief(BaseModel):
    id: int
    status: ApplicationStatus
    job: JobBrief


class InterviewListItem(InterviewOut):
    application: ApplicationBrief
    student: StudentBrief | None = None


class ApplicationSummary(BaseModel):
    id: int
    status: ApplicationStatus
    applied_at: datetime
    updated_at: datetime
    job: JobBrief
    student: StudentBrief
    interview_count: int
    next_interview: datetime | None
    can_withdraw: bool


class EligibilityNow(BaseModel):
    """Eligibility computed from the student's CURRENT profile (not stored)."""

    result: str
    eligible: bool
    summary: str
    failed_requirements: list[str]
    incomplete_fields: list[str]
    criteria: list[CriterionOut]


class ApplicationDetail(ApplicationSummary):
    interviews: list[InterviewOut]
    eligibility_now: EligibilityNow


class ApplicationList(BaseModel):
    items: list[ApplicationSummary]
    total: int
    limit: int
    offset: int
    counts: dict[str, int]  # applications per status across the whole (filtered) list


class InterviewList(BaseModel):
    items: list[InterviewListItem]
    total: int
    counts: dict[str, int]  # upcoming / past / unscheduled / needs_result
