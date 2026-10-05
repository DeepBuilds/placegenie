from typing import Literal

from pydantic import BaseModel, ConfigDict


class CriterionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    status: Literal["passed", "failed", "not_evaluated"]
    required: str
    actual: str
    message: str


class JobRef(BaseModel):
    id: int
    title: str
    company: str


class EligibilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job: JobRef
    result: Literal["ELIGIBLE", "NOT_ELIGIBLE", "INCOMPLETE_PROFILE"]
    eligible: bool
    summary: str
    criteria: list[CriterionOut]
    failed_requirements: list[str]
    reasons: list[str]
    missing_skills: list[str]
    missing_preferred_skills: list[str]
    missing_certifications: list[str]
    incomplete_fields: list[str]
