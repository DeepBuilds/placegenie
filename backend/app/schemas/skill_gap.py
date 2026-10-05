from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.eligibility import JobRef

Level = Literal["high", "medium", "low"]


class MatchedSkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: int
    name: str
    category: str | None
    required: bool
    essential: bool
    weight: int
    student_level: str | None


class MissingSkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: int
    name: str
    category: str | None
    required: bool
    essential: bool
    weight: int
    priority: Level
    reasons: list[str]
    jobs_requiring: int
    demand_share: float


class PriorityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    skill_id: int
    name: str
    level: Level
    reasons: list[str]


class SkillGapOut(BaseModel):
    job: JobRef
    has_requirements: bool
    match_percentage: int | None
    required_match_percentage: int | None
    matched_count: int
    missing_count: int
    total_count: int
    required_total: int
    required_matched: int
    matched_skills: list[MatchedSkillOut]
    missing_skills: list[MissingSkillOut]
    priority: list[PriorityOut]
    student_has_skills: bool
    summary: str
    notes: list[str]
    open_jobs_compared: int  # how many open jobs the "asked for in N jobs" figures are based on
    disclaimer: str
