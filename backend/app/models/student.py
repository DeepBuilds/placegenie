import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.company import JobType
from app.models.user import User


class Proficiency(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class SkillSource(str, enum.Enum):
    MANUAL = "manual"
    RESUME = "resume"


# Pure many-to-many link tables (no extra columns).
student_preferred_roles = Table(
    "student_preferred_roles",
    Base.metadata,
    Column("student_id", ForeignKey("students.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("job_roles.id", ondelete="CASCADE"), primary_key=True),
)

student_preferred_companies = Table(
    "student_preferred_companies",
    Base.metadata,
    Column("student_id", ForeignKey("students.id", ondelete="CASCADE"), primary_key=True),
    Column("company_id", ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True),
)


class Student(TimestampMixin, Base):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("cgpa >= 0 AND cgpa <= 10", name="ck_students_cgpa_range"),
        CheckConstraint("backlogs >= 0", name="ck_students_backlogs_nonneg"),
        CheckConstraint("year BETWEEN 1 AND 6", name="ck_students_year_range"),
        CheckConstraint("semester BETWEEN 1 AND 12", name="ck_students_semester_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    college: Mapped[str | None] = mapped_column(String(150))
    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("branches.id", ondelete="SET NULL"), index=True
    )
    year: Mapped[int | None] = mapped_column(Integer)
    semester: Mapped[int | None] = mapped_column(Integer)
    cgpa: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    backlogs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    interests: Mapped[str | None] = mapped_column(Text)
    preferred_location: Mapped[str | None] = mapped_column(String(100))
    preferred_job_type: Mapped[JobType | None] = mapped_column(
        Enum(JobType, native_enum=False, length=20)
    )

    user: Mapped[User] = relationship(back_populates="student")
    branch = relationship("Branch")
    skills: Mapped[list["StudentSkill"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    certifications: Mapped[list["Certification"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    experiences: Mapped[list["Experience"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    preferred_roles = relationship("JobRole", secondary=student_preferred_roles)
    preferred_companies = relationship("Company", secondary=student_preferred_companies)
    resumes = relationship("Resume", back_populates="student", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="student", cascade="all, delete-orphan")
    conversations = relationship("ChatConversation", back_populates="student", cascade="all, delete-orphan")


class StudentSkill(TimestampMixin, Base):
    __tablename__ = "student_skills"

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    proficiency: Mapped[Proficiency] = mapped_column(
        Enum(Proficiency, native_enum=False, length=20), default=Proficiency.BEGINNER, nullable=False
    )
    source: Mapped[SkillSource] = mapped_column(
        Enum(SkillSource, native_enum=False, length=20), default=SkillSource.MANUAL, nullable=False
    )

    student: Mapped[Student] = relationship(back_populates="skills")
    skill = relationship("Skill")


class Certification(TimestampMixin, Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(100))
    issued_on: Mapped[date | None] = mapped_column(Date)

    student: Mapped[Student] = relationship(back_populates="certifications")


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tech_stack: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(255))

    student: Mapped[Student] = relationship(back_populates="projects")


class Experience(TimestampMixin, Base):
    __tablename__ = "experiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    organization: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)

    student: Mapped[Student] = relationship(back_populates="experiences")
