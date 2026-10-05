from typing import Literal

from pydantic import BaseModel

from app.schemas.job import JobOut


class ComponentOut(BaseModel):
    key: str
    label: str
    available: bool  # False = no data for this component, so it was left out of the score
    weight: float  # effective weight after rescaling over the available components
    score: float  # 0..1
    points: float  # contribution to the 0..100 fit (before the eligibility multiplier)
    note: str


class RecEligibility(BaseModel):
    result: Literal["ELIGIBLE", "NOT_ELIGIBLE", "INCOMPLETE_PROFILE"]
    eligible: bool
    multiplier: float
    failed_requirements: list[str]
    incomplete_fields: list[str]


class RecommendationOut(BaseModel):
    job: JobOut
    match_score: int  # 0..100
    eligibility: RecEligibility
    matched_skills: list[str]
    missing_skills: list[str]  # required skills the student lacks
    missing_preferred_skills: list[str]
    reasons: list[str]  # why it was recommended
    concerns: list[str]  # what holds it back
    breakdown: list[ComponentOut]


class EligibilityCounts(BaseModel):
    eligible: int
    incomplete_profile: int
    not_eligible: int


class RecommendationPage(BaseModel):
    items: list[RecommendationOut]
    total: int  # after filters (including eligible_only)
    limit: int
    offset: int
    counts: EligibilityCounts  # across all candidate jobs, before eligible_only
    profile_hints: list[str]
