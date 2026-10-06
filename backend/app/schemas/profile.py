import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import JobType, Proficiency, SkillSource
from app.schemas.ids import BodyId

PHONE_RE = re.compile(r"^\+?[0-9][0-9 \-]{6,18}[0-9]$")
URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


def _strip_or_none(v: str | None) -> str | None:
    if v is None:
        return None
    v = " ".join(v.split())
    return v or None


# ---------- lookups ----------
class NamedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class CategorizedOut(NamedOut):
    category: str | None


# ---------- basic / academic ----------
class ProfileUpdate(BaseModel):
    """Full replacement of the basic profile fields (PUT semantics)."""

    full_name: str = Field(min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    college: str | None = Field(default=None, max_length=150)
    branch_id: BodyId | None = None
    year: int | None = Field(default=None, ge=1, le=6)
    semester: int | None = Field(default=None, ge=1, le=12)
    cgpa: float | None = Field(default=None, ge=0, le=10)
    backlogs: int = Field(default=0, ge=0, le=50)
    interests: str | None = Field(default=None, max_length=1000)
    preferred_location: str | None = Field(default=None, max_length=100)
    preferred_job_type: JobType | None = None

    _clean = field_validator("full_name", "college", "interests", "preferred_location")(
        classmethod(lambda cls, v: _strip_or_none(v))
    )

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: str | None) -> str | None:
        v = _strip_or_none(v)
        if v is not None and not PHONE_RE.match(v):
            raise ValueError("Enter a valid phone number (digits, optional +, spaces or dashes).")
        return v

    @field_validator("cgpa")
    @classmethod
    def two_decimals(cls, v: float | None) -> float | None:
        return None if v is None else round(v, 2)

    @model_validator(mode="after")
    def check_consistency(self):
        if not self.full_name or len(self.full_name) < 2:
            raise ValueError("Name must be at least 2 characters.")
        # Semester system: year N contains semesters 2N-1 and 2N.
        if self.year and self.semester and self.semester not in (2 * self.year - 1, 2 * self.year):
            raise ValueError(
                f"Semester {self.semester} does not match year {self.year} "
                f"(expected {2 * self.year - 1} or {2 * self.year})."
            )
        return self


# ---------- skills ----------
class SkillEntry(BaseModel):
    skill_id: BodyId
    proficiency: Proficiency = Proficiency.BEGINNER


class SkillsUpdate(BaseModel):
    skills: list[SkillEntry] = Field(max_length=100)

    @field_validator("skills")
    @classmethod
    def no_duplicates(cls, v: list[SkillEntry]) -> list[SkillEntry]:
        ids = [s.skill_id for s in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Each skill can only be added once.")
        return v


class StudentSkillOut(BaseModel):
    skill_id: int
    name: str
    category: str | None
    proficiency: Proficiency
    source: SkillSource


# ---------- certifications ----------
class CertificationIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    issuer: str | None = Field(default=None, max_length=100)
    issued_on: date | None = None

    _clean = field_validator("name", "issuer")(classmethod(lambda cls, v: _strip_or_none(v)))

    @field_validator("issued_on")
    @classmethod
    def not_future(cls, v: date | None) -> date | None:
        if v and v > date.today():
            raise ValueError("Issue date cannot be in the future.")
        return v


class CertificationOut(CertificationIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- projects ----------
class ProjectIn(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    tech_stack: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=255)

    _clean = field_validator("title", "tech_stack")(classmethod(lambda cls, v: _strip_or_none(v)))

    @field_validator("description")
    @classmethod
    def strip_description(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v else None

    @field_validator("url")
    @classmethod
    def valid_url(cls, v: str | None) -> str | None:
        v = _strip_or_none(v)
        if v is not None and not URL_RE.match(v):
            raise ValueError("Link must start with http:// or https://")
        return v


class ProjectOut(ProjectIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- experience ----------
class ExperienceIn(BaseModel):
    organization: str = Field(min_length=2, max_length=150)
    role: str = Field(min_length=2, max_length=100)
    start_date: date | None = None
    end_date: date | None = None  # empty = ongoing
    description: str | None = Field(default=None, max_length=2000)

    _clean = field_validator("organization", "role")(classmethod(lambda cls, v: _strip_or_none(v)))

    @model_validator(mode="after")
    def check_dates(self):
        if self.start_date and self.start_date > date.today():
            raise ValueError("Start date cannot be in the future.")
        if self.end_date and not self.start_date:
            raise ValueError("Enter a start date when giving an end date.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date cannot be before the start date.")
        return self


class ExperienceOut(ExperienceIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- preferences ----------
class PreferencesUpdate(BaseModel):
    preferred_role_ids: list[BodyId] = Field(default_factory=list, max_length=10)
    preferred_company_ids: list[BodyId] = Field(default_factory=list, max_length=20)


# ---------- full profile ----------
class Completeness(BaseModel):
    score: int  # 0-100
    missing: list[str]


class ProfileOut(BaseModel):
    id: int
    email: str
    full_name: str
    phone: str | None
    college: str | None
    branch: NamedOut | None
    year: int | None
    semester: int | None
    cgpa: float | None
    backlogs: int
    interests: str | None
    preferred_location: str | None
    preferred_job_type: JobType | None
    skills: list[StudentSkillOut]
    certifications: list[CertificationOut]
    projects: list[ProjectOut]
    experiences: list[ExperienceOut]
    preferred_roles: list[NamedOut]
    preferred_companies: list[NamedOut]
    completeness: Completeness
