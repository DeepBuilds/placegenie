from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.coordinator import BranchStats, CgpaBand, CohortProgress, CompanyStats, InterviewOutcomes, PlacementRate, StageStep, StatusCount
from app.schemas.dashboard import ProgressSection, RecommendationsSection, SkillGapsSection, StudentCard


# ---------------------------------------------------------------- student report
class ReportApplication(BaseModel):
    id: int
    job_id: int
    job_title: str
    company: str
    status: str
    applied_at: datetime
    updated_at: datetime
    interviews: int
    next_interview: datetime | None


class ReportInterview(BaseModel):
    id: int
    application_id: int
    job_title: str
    company: str
    stage: str
    scheduled_at: datetime | None
    outcome: str


class ApplicationSummary(BaseModel):
    total: int  # every application record
    active: int  # not withdrawn
    awaiting_review: int
    in_process: int  # shortlisted, online assessment, technical or HR interview
    selected: int
    rejected: int
    withdrawn: int
    outcome: str  # placed | in_process | applied | rejected | not_applied  (the student's overall standing)
    outcome_label: str


class InterviewReport(BaseModel):
    total: int
    passed: int
    not_cleared: int
    pending: int
    upcoming: int
    pass_rate: int | None  # of interviews with a recorded result
    items: list[ReportInterview]


class StudentReport(BaseModel):
    generated_at: datetime
    student: StudentCard
    summary: ApplicationSummary
    status_distribution: list[StatusCount]
    applications: list[ReportApplication]
    interviews: InterviewReport
    recommended: RecommendationsSection | None
    skill_gaps: SkillGapsSection | None
    progress: ProgressSection | None
    errors: dict[str, str]


# ---------------------------------------------------------------- coordinator report
class PlacementStats(BaseModel):
    total_students: int
    applicants: int  # at least one application that is not withdrawn
    placed: int
    in_process: int
    rejected: int  # every remaining application rejected
    not_applied: int
    placement_rate: PlacementRate
    by_stage: list[StageStep]
    by_branch: list[BranchStats]
    by_cgpa: list[CgpaBand]


class JobStats(BaseModel):
    job_id: int
    title: str
    company: str
    status: str
    deadline: date | None
    applications: int  # every record, including withdrawn
    awaiting_review: int
    in_process: int
    selected: int
    rejected: int
    withdrawn: int


class SelectedStudent(BaseModel):
    student_id: int
    name: str
    email: str
    branch: str | None
    cgpa: float | None
    company: str
    job_title: str
    selected_on: date  # when the application was last updated, i.e. when it was marked selected


class SkillGap(BaseModel):
    skill: str
    jobs_requiring: int  # open jobs that ask for it
    students_with: int
    students_lacking: int
    percent_lacking: int  # of all students


class CoordinatorReport(BaseModel):
    generated_at: datetime
    placement: PlacementStats
    status_distribution: list[StatusCount]
    companies: list[CompanyStats]
    jobs: list[JobStats]
    selected_students: list[SelectedStudent]
    skill_gaps: list[SkillGap]
    interviews: InterviewOutcomes
    progress: CohortProgress
    min_group_size: int
