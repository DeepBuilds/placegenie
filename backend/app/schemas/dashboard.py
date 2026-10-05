from datetime import date, datetime

from pydantic import BaseModel

from app.models import ApplicationStatus


class StudentCard(BaseModel):
    name: str
    first_name: str
    branch: str | None
    year: int | None
    semester: int | None
    cgpa: float | None


class ProfileSection(BaseModel):
    score: int  # 0-100 completeness
    missing: list[str]
    skills: int
    projects: int
    certifications: int


class ResumeSection(BaseModel):
    uploaded: bool
    filename: str | None = None
    uploaded_at: datetime | None = None
    completeness_score: int | None = None
    skills_detected: int | None = None
    top_suggestions: list[str] = []


class JobCard(BaseModel):
    job_id: int
    title: str
    company: str
    location: str | None
    deadline: date | None
    match_score: int
    eligibility: str  # ELIGIBLE | NOT_ELIGIBLE | INCOMPLETE_PROFILE
    missing_skills: list[str]
    already_applied: bool


class RecommendationsSection(BaseModel):
    open_jobs: int
    eligible: int
    incomplete_profile: int
    not_eligible: int
    top: list[JobCard]  # best matches overall
    hints: list[str]  # what to add to the profile for better recommendations


class OpportunitiesSection(BaseModel):
    eligible_count: int
    eligible_percent: int  # of all open jobs
    items: list[JobCard]  # best eligible jobs not yet applied to
    closing_soon: list[JobCard]  # deadline within 7 days, not applied, not known to be ineligible


class ApplicationItem(BaseModel):
    id: int
    job_title: str
    company: str
    status: ApplicationStatus
    applied_at: datetime
    next_interview: datetime | None


class ApplicationsSection(BaseModel):
    total: int
    active: int  # not withdrawn
    by_status: dict[str, int]
    recent: list[ApplicationItem]


class InterviewItem(BaseModel):
    id: int
    application_id: int
    stage: str
    scheduled_at: datetime | None
    job_title: str
    company: str


class InterviewsSection(BaseModel):
    upcoming: list[InterviewItem]
    upcoming_count: int
    needs_result: int
    total: int
    passed: int
    not_cleared: int
    pending: int


class MissingSkill(BaseModel):
    name: str
    jobs_needing: int
    example_jobs: list[str]


class ClosestJob(BaseModel):
    job_id: int
    title: str
    company: str
    match_score: int
    missing_skills: list[str]


class SkillGapsSection(BaseModel):
    student_has_skills: bool
    based_on_jobs: int  # how many of the best-matching jobs were looked at
    top_missing: list[MissingSkill]
    closest_job: ClosestJob | None


class Milestone(BaseModel):
    key: str
    label: str
    done: bool
    detail: str
    link: str


class NextStep(BaseModel):
    key: str
    label: str
    reason: str
    link: str


class ProgressSection(BaseModel):
    percent: int
    done: int
    total: int
    milestones: list[Milestone]
    next_step: NextStep | None


class DemandSkill(BaseModel):
    name: str
    jobs: int
    you_have: bool


class FunnelStep(BaseModel):
    status: str
    count: int


class StatisticsSection(BaseModel):
    open_jobs: int
    companies_hiring: int
    closing_this_week: int
    eligible_percent: int
    in_demand_skills: list[DemandSkill]
    application_funnel: list[FunnelStep]
    interview_pass_rate: int | None  # of interviews with a recorded result


class DashboardOut(BaseModel):
    generated_at: datetime
    student: StudentCard
    profile: ProfileSection | None
    resume: ResumeSection | None
    recommendations: RecommendationsSection | None
    opportunities: OpportunitiesSection | None
    applications: ApplicationsSection | None
    interviews: InterviewsSection | None
    skill_gaps: SkillGapsSection | None
    progress: ProgressSection | None
    statistics: StatisticsSection | None
    errors: dict[str, str]  # a section that failed is null here and explained in this map
