from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TokenError, decode_access_token
from app.database.session import get_db
from app.models import Role, User
from app.repositories import user_repository

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _unauthorized("Not authenticated. Please log in.")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except TokenError as exc:
        raise _unauthorized(str(exc)) from exc
    except ValueError:
        raise _unauthorized("Invalid authentication token.")

    user = user_repository.get_by_id(db, user_id)
    # The role is read from the database, not the token, so role changes apply immediately.
    if user is None or not user.is_active:
        raise _unauthorized("Account not found or disabled.")
    return user


def require_roles(*roles: Role) -> Callable[..., User]:
    """Dependency factory: allow only users whose role is in `roles`."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return user

    return checker


require_student = require_roles(Role.STUDENT)
require_coordinator = require_roles(Role.COORDINATOR)
