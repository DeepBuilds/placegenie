from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Coordinator, Role, Student, User


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create_user_with_profile(
    db: Session, *, email: str, password_hash: str, role: Role, full_name: str
) -> User:
    """Create the user and its role profile in a single transaction."""
    user = User(email=email, password_hash=password_hash, role=role)
    if role == Role.STUDENT:
        user.student = Student(full_name=full_name)
    else:
        user.coordinator = Coordinator(full_name=full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
