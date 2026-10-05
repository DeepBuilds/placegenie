import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class JobType(str, enum.Enum):
    FULL_TIME = "full_time"
    INTERNSHIP = "internship"
    CONTRACT = "contract"


class JobStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"


class SkillImportance(str, enum.Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100))
    website: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)

    jobs: Mapped[list["Job"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("min_cgpa >= 0 AND min_cgpa <= 10", name="ck_jobs_min_cgpa_range"),
        CheckConstraint("max_backlogs >= 0", name="ck_jobs_max_backlogs_nonneg"),
        CheckConstraint("min_experience_months >= 0", name="ck_jobs_min_exp_nonneg"),
        Index("ix_jobs_status_deadline", "status", "deadline"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_roles.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(100))
    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType, native_enum=False, length=20), default=JobType.FULL_TIME, nullable=False
    )
    # Eligibility criteria: min_cgpa 0 / NULL max_backlogs / 0 experience mean "no restriction".
    min_cgpa: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=0, nullable=False)
    max_backlogs: Mapped[int | None] = mapped_column(Integer)
    min_experience_months: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deadline: Mapped[date | None] = mapped_column(Date)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, length=20), default=JobStatus.OPEN, nullable=False
    )

    company: Mapped[Company] = relationship(back_populates="jobs")
    role = relationship("JobRole")
    skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    allowed_branches: Mapped[list["JobAllowedBranch"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    required_certifications: Mapped[list["JobRequiredCertification"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")


class JobSkill(Base):
    __tablename__ = "job_skills"
    __table_args__ = (CheckConstraint("weight >= 1", name="ck_job_skills_weight_pos"),)

    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    importance: Mapped[SkillImportance] = mapped_column(
        Enum(SkillImportance, native_enum=False, length=20),
        default=SkillImportance.REQUIRED,
        nullable=False,
    )
    weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    job: Mapped[Job] = relationship(back_populates="skills")
    skill = relationship("Skill")


class JobAllowedBranch(Base):
    """No rows for a job means every branch is allowed."""

    __tablename__ = "job_allowed_branches"

    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), primary_key=True
    )

    job: Mapped[Job] = relationship(back_populates="allowed_branches")
    branch = relationship("Branch")


class JobRequiredCertification(Base):
    __tablename__ = "job_required_certifications"

    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    certification_name: Mapped[str] = mapped_column(String(150), primary_key=True)

    job: Mapped[Job] = relationship(back_populates="required_certifications")
