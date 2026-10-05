from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

LongText = Text().with_variant(mysql.LONGTEXT(), "mysql")


class Resume(TimestampMixin, Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)  # server-generated name
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(LongText)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    student = relationship("Student", back_populates="resumes")
    analysis: Mapped["ResumeAnalysis | None"] = relationship(
        back_populates="resume", uselist=False, cascade="all, delete-orphan"
    )


class ResumeAnalysis(TimestampMixin, Base):
    """Stored result of analysing one resume.

    The JSON columns are display-only (never queried); detected skills are
    relational in ResumeDetectedSkill.
    """

    __tablename__ = "resume_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    completeness_score: Mapped[int | None] = mapped_column(Integer)
    education: Mapped[list | None] = mapped_column(JSON)
    projects: Mapped[list | None] = mapped_column(JSON)
    experience: Mapped[list | None] = mapped_column(JSON)
    certifications: Mapped[list | None] = mapped_column(JSON)
    suggestions: Mapped[list | None] = mapped_column(JSON)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    resume: Mapped[Resume] = relationship(back_populates="analysis")
    detected_skills: Mapped[list["ResumeDetectedSkill"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class ResumeDetectedSkill(Base):
    __tablename__ = "resume_detected_skills"

    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("resume_analyses.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True, index=True
    )

    analysis: Mapped[ResumeAnalysis] = relationship(back_populates="detected_skills")
    skill = relationship("Skill")
