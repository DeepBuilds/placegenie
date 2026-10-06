import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import JobStatus, JobType, SkillImportance
from app.schemas.ids import BodyId

URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


def _clean(v: str | None) -> str | None:
    if v is None:
        return None
    v = " ".join(v.split())
    return v or None


# ---------- companies ----------
class CompanyIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    industry: str | None = Field(default=None, max_length=100)
    website: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=3000)

    _clean = field_validator("name", "industry", "location")(classmethod(lambda cls, v: _clean(v)))

    @field_validator("description")
    @classmethod
    def strip_description(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v else None

    @field_validator("website")
    @classmethod
    def valid_website(cls, v: str | None) -> str | None:
        v = _clean(v)
        if v is not None and not URL_RE.match(v):
            raise ValueError("Website must start with http:// or https://")
        return v


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    industry: str | None
    website: str | None
    location: str | None
    description: str | None
    open_jobs: int = 0


class CompanyBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    industry: str | None
    location: str | None


# ---------- jobs ----------
class JobSkillIn(BaseModel):
    skill_id: BodyId
    importance: SkillImportance = SkillImportance.REQUIRED
    weight: int = Field(default=1, ge=1, le=5)


class JobIn(BaseModel):
    """Full replacement of a job (used for both create and update)."""

    company_id: BodyId
    role_id: BodyId | None = None
    title: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=100)
    job_type: JobType = JobType.FULL_TIME
    min_cgpa: float = Field(default=0, ge=0, le=10)
    max_backlogs: int | None = Field(default=None, ge=0, le=50)  # None = no limit
    min_experience_months: int = Field(default=0, ge=0, le=120)
    deadline: date | None = None
    status: JobStatus = JobStatus.OPEN
    skills: list[JobSkillIn] = Field(default_factory=list, max_length=30)
    allowed_branch_ids: list[BodyId] = Field(default_factory=list, max_length=20)  # empty = all branches
    required_certifications: list[str] = Field(default_factory=list, max_length=10)

    _clean = field_validator("title", "location")(classmethod(lambda cls, v: _clean(v)))

    @field_validator("description")
    @classmethod
    def strip_description(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v else None

    @field_validator("min_cgpa")
    @classmethod
    def two_decimals(cls, v: float) -> float:
        return round(v, 2)

    @field_validator("required_certifications")
    @classmethod
    def clean_certs(cls, v: list[str]) -> list[str]:
        cleaned = []
        for name in v:
            name = " ".join(name.split())
            if not 2 <= len(name) <= 150:
                raise ValueError("Each certification name must be 2-150 characters.")
            if name.lower() not in {c.lower() for c in cleaned}:
                cleaned.append(name)
        return cleaned

    @model_validator(mode="after")
    def no_duplicates(self):
        if len({s.skill_id for s in self.skills}) != len(self.skills):
            raise ValueError("Each skill can only be listed once.")
        if len(set(self.allowed_branch_ids)) != len(self.allowed_branch_ids):
            raise ValueError("Each branch can only be listed once.")
        return self


class JobSkillOut(BaseModel):
    skill_id: int
    name: str
    category: str | None
    importance: SkillImportance
    weight: int


class NamedRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class JobOut(BaseModel):
    id: int
    title: str
    description: str | None
    location: str | None
    job_type: JobType
    min_cgpa: float
    max_backlogs: int | None
    min_experience_months: int
    deadline: date | None
    is_expired: bool
    status: JobStatus
    company: CompanyBrief
    role: NamedRef | None
    skills: list[JobSkillOut]
    allowed_branches: list[NamedRef]  # empty = every branch is allowed
    required_certifications: list[str]
    created_at: datetime


class JobPage(BaseModel):
    items: list[JobOut]
    total: int
    limit: int
    offset: int
