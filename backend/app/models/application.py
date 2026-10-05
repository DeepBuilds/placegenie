import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class ApplicationStatus(str, enum.Enum):
    APPLIED = "applied"
    SHORTLISTED = "shortlisted"
    ONLINE_ASSESSMENT = "online_assessment"
    TECHNICAL_INTERVIEW = "technical_interview"
    HR_INTERVIEW = "hr_interview"
    SELECTED = "selected"
    REJECTED = "rejected"


class InterviewStageType(str, enum.Enum):
    ONLINE_ASSESSMENT = "online_assessment"
    TECHNICAL_INTERVIEW = "technical_interview"
    HR_INTERVIEW = "hr_interview"


class StageOutcome(str, enum.Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class Application(TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("student_id", "job_id", name="uq_applications_student_job"),
        Index("ix_applications_student_status", "student_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, native_enum=False, length=30),
        default=ApplicationStatus.APPLIED,
        nullable=False,
    )
    applied_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    student = relationship("Student", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    interview_stages: Mapped[list["InterviewStage"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="InterviewStage.scheduled_at",
    )


class InterviewStage(TimestampMixin, Base):
    __tablename__ = "interview_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    stage: Mapped[InterviewStageType] = mapped_column(
        Enum(InterviewStageType, native_enum=False, length=30), nullable=False
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    outcome: Mapped[StageOutcome] = mapped_column(
        Enum(StageOutcome, native_enum=False, length=20), default=StageOutcome.PENDING, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)

    application: Mapped[Application] = relationship(back_populates="interview_stages")
