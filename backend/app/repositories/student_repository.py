from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Branch, JobRole, Skill, Student, StudentSkill


def get_profile_by_user_id(db: Session, user_id: int) -> Student | None:
    """Load a student with everything the profile page shows, in a few queries."""
    return db.scalar(
        select(Student)
        .where(Student.user_id == user_id)
        .options(
            selectinload(Student.user),
            selectinload(Student.branch),
            selectinload(Student.skills).selectinload(StudentSkill.skill),
            selectinload(Student.certifications),
            selectinload(Student.projects),
            selectinload(Student.experiences),
            selectinload(Student.preferred_roles),
            selectinload(Student.preferred_companies),
        )
    )


def get_owned(db: Session, model, item_id: int, student_id: int):
    """Fetch a child row (certification/project/experience) only if it belongs to the student."""
    return db.scalar(select(model).where(model.id == item_id, model.student_id == student_id))


def get_branch(db: Session, branch_id: int) -> Branch | None:
    return db.get(Branch, branch_id)


def get_by_ids(db: Session, model, ids: list[int]) -> list:
    if not ids:
        return []
    return list(db.scalars(select(model).where(model.id.in_(ids))))


def list_branches(db: Session) -> list[Branch]:
    return list(db.scalars(select(Branch).order_by(Branch.name)))


def list_skills(db: Session) -> list[Skill]:
    return list(db.scalars(select(Skill).order_by(Skill.category, Skill.name)))


def list_job_roles(db: Session) -> list[JobRole]:
    return list(db.scalars(select(JobRole).order_by(JobRole.name)))
