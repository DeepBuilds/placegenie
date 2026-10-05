from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import DUMMY_HASH, create_access_token, hash_password, verify_password
from app.models import Role, User
from app.repositories import user_repository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        user=UserOut.model_validate(user),
    )


def _email_taken() -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")


def register_student(db: Session, data: RegisterRequest) -> TokenResponse:
    """Public registration always creates a student; coordinators are created by an admin script."""
    if user_repository.get_by_email(db, data.email):
        raise _email_taken()
    try:
        user = user_repository.create_user_with_profile(
            db,
            email=data.email,
            password_hash=hash_password(data.password),
            role=Role.STUDENT,
            full_name=data.full_name,
        )
    except IntegrityError:  # two simultaneous registrations with the same email
        db.rollback()
        raise _email_taken()
    return _token_response(user)


def login(db: Session, data: LoginRequest) -> TokenResponse:
    user = user_repository.get_by_email(db, data.email)
    # Always run one bcrypt check so response time does not reveal whether the email exists.
    password_ok = verify_password(data.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been disabled.")
    return _token_response(user)
