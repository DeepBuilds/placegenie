from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.application import ApplicationList, InterviewList
from app.schemas.dashboard import ProgressSection, ResumeSection, SkillGapsSection
from app.schemas.profile import ProfileOut


# ---------------------------------------------------------------- dashboard
class PlacementRate(BaseModel):
    percent: int | None  # null until there is enough data to mean something
    placed: int
    total_students: int
    sufficient_data: bool
    note: str


class CoordinatorStats(BaseModel):
    total_students: int
    total_companies: int
    total_jobs: int
    open_jobs: int
    total_applications: int  # every application record, including withdrawn ones
    withdrawn_applications: int
    applicants: int  # students with at least one application that is not withdrawn
    shortlisted_students: int  # students with an application being considered (shortlisted .. HR interview)
    selected_students: int
    rejected_applications: int
    placement_rate: PlacementRate


class StatusCount(BaseModel):
    status: str
    count: int


class RecentApplication(BaseModel):
    id: int
    student_id: int
    student_name: str
    job_title: str
    company: str
    status: str
    applied_at: datetime


class ClosingJob(BaseModel):
    job_id: int
    title: str
    company: str
    deadline: date
    applications: int


class Attention(BaseModel):
    awaiting_review: int  # applications still in the first status ("applied")
    closing_soon: list[ClosingJob]  # open jobs whose deadline is within 7 days
    open_jobs_without_applications: int
    interviews_this_week: int


class CoordinatorDashboard(BaseModel):
    generated_at: datetime
    stats: CoordinatorStats
    application_funnel: list[StatusCount]
    recent_applications: list[RecentApplication]
    attention: Attention


# ---------------------------------------------------------------- students
class BranchRef(BaseModel):
    id: int
    name: str


class StudentRow(BaseModel):
    id: int
    full_name: str
    email: str
    college: str | None
    branch: BranchRef | None
    year: int | None
    semester: int | None
    cgpa: float | None
    backlogs: int
    profile_percent: int
    has_resume: bool
    applications: int  # not counting withdrawn
    stage: str  # placed | in_process | applied | rejected | not_applied


class StudentPage(BaseModel):
    items: list[StudentRow]
    total: int
    limit: int
    offset: int
    stage_counts: dict[str, int]  # across the whole cohort, ignoring the stage filter


class StudentDetail(BaseModel):
    """A student's placement profile, assembled from the same services the student's own pages use."""

    student_id: int
    stage: str
    profile: ProfileOut
    resume: ResumeSection | None
    progress: ProgressSection | None
    skill_gaps: SkillGapsSection | None
    applications: ApplicationList
    interviews: InterviewList
    errors: dict[str, str]


# ---------------------------------------------------------------- progress & analytics
class StageStep(BaseModel):
    key: str
    label: str
    count: int
    percent: int  # of all students


class CohortProgress(BaseModel):
    total_students: int
    funnel: list[StageStep]  # how many students reached each milestone (same milestones as the student's own tracker)
    current_stage: list[StageStep]  # where each student is right now
    needs_attention: dict[str, int]  # e.g. students with no resume


class CompanyStats(BaseModel):
    company: str
    jobs: int
    applications: int
    shortlisted: int
    selected: int
    rejected: int


class BranchStats(BaseModel):
    branch: str
    students: int
    applicants: int
    placed: int
    placement_rate: int | None  # null for a branch with too few students


class CgpaBand(BaseModel):
    band: str
    students: int
    placed: int
    placement_rate: int | None


class SkillSupply(BaseModel):
    skill: str
    jobs_requiring: int  # open jobs that ask for it
    students_with: int
    students_percent: int


class InterviewOutcomes(BaseModel):
    total: int
    passed: int
    not_cleared: int
    pending: int
    pass_rate: int | None


class Analytics(BaseModel):
    status_funnel: list[StatusCount]
    by_company: list[CompanyStats]
    by_branch: list[BranchStats]
    by_cgpa: list[CgpaBand]
    skill_supply: list[SkillSupply]  # most requested skills first, with how many students have them
    interview_outcomes: InterviewOutcomes
    min_group_size: int  # rates are hidden for groups smaller than this
