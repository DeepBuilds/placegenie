from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Resume, ResumeAnalysis, ResumeDetectedSkill, Skill


def _options():
    return (
        selectinload(Resume.analysis)
        .selectinload(ResumeAnalysis.detected_skills)
        .selectinload(ResumeDetectedSkill.skill),
    )


def get_current(db: Session, student_id: int) -> Resume | None:
    """The student's active resume (there is at most one)."""
    return db.scalar(
        select(Resume)
        .where(Resume.student_id == student_id, Resume.is_active.is_(True))
        .order_by(Resume.id.desc())
        .options(*_options())
    )


def get_owned(db: Session, resume_id: int, student_id: int) -> Resume | None:
    """A resume only if it belongs to this student; other students' ids look like 'not found'."""
    return db.scalar(
        select(Resume).where(Resume.id == resume_id, Resume.student_id == student_id).options(*_options())
    )


def list_all(db: Session, student_id: int) -> list[Resume]:
    return list(db.scalars(select(Resume).where(Resume.student_id == student_id)))


def skill_catalog(db: Session) -> list[tuple[int, str, str | None]]:
    return [(s.id, s.name, s.category) for s in db.scalars(select(Skill))]
