from datetime import datetime

from pydantic import BaseModel


class ResumeOut(BaseModel):
    id: int
    original_name: str
    size_bytes: int
    page_count: int | None
    uploaded_at: datetime


class SectionOut(BaseModel):
    key: str
    label: str
    required: bool = False  # core sections every resume should have


class ContactOut(BaseModel):
    email: bool
    phone: bool
    linkedin: bool
    github: bool


class EducationEntry(BaseModel):
    degree: str | None = None
    institution: str | None = None
    years: str | None = None
    cgpa: float | None = None
    percentage: float | None = None
    text: str = ""


class EntryOut(BaseModel):
    title: str
    dates: str | None = None
    description: str = ""
    bullets: list[str] = []
    skills: list[str] = []  # known skills mentioned in this entry (projects)


class DetectedSkillOut(BaseModel):
    skill_id: int
    name: str
    category: str | None
    evidence: list[str]  # sections where it was found
    in_profile: bool


class SuggestionOut(BaseModel):
    severity: str  # high | medium | low
    category: str
    text: str


class ScorePartOut(BaseModel):
    label: str
    earned: int
    max: int
    note: str


class JobRelevanceOut(BaseModel):
    job_id: int
    title: str
    company: str
    relevance: int  # 0..100
    matched_skills: list[str]
    missing_skills: list[str]


class MissingSkillOut(BaseModel):
    name: str
    jobs_requiring: int
    example_jobs: list[str]


class ProfileSkillRef(BaseModel):
    skill_id: int
    name: str


class ProfileComparisonOut(BaseModel):
    skills_not_in_profile: list[ProfileSkillRef]
    skills_not_on_resume: list[str]
    resume_cgpa: float | None
    profile_cgpa: float | None
    cgpa_mismatch: bool
    missing_profile_information: list[str]


class ResumeAnalysisOut(BaseModel):
    resume: ResumeOut
    detected_name: str | None
    word_count: int
    page_count: int
    completeness_score: int
    score_breakdown: list[ScorePartOut]
    sections_found: list[SectionOut]
    sections_missing: list[SectionOut]
    contact: ContactOut
    education: list[EducationEntry]
    projects: list[EntryOut]
    experience: list[EntryOut]
    certifications: list[str]
    skills: list[DetectedSkillOut]
    keywords: list[str]
    potentially_missing_skills: list[MissingSkillOut]
    job_relevance: list[JobRelevanceOut]
    profile_comparison: ProfileComparisonOut
    suggestions: list[SuggestionOut]
    disclaimer: str
