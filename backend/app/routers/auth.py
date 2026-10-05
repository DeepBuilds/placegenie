from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new student account and sign in."""
    return auth_service.register_student(db, data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Log in as a student or coordinator. The returned `user.role` decides the dashboard."""
    return auth_service.login(db, data)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """Current user (the frontend uses this to validate a stored token)."""
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(_: User = Depends(get_current_user)):
    """Tokens are stateless JWTs, so logout means the client discards its token.

    The endpoint gives the client a single call to make and lets server-side
    token revocation be added later without changing the API.
    """
    return Response(status_code=status.HTTP_204_NO_CONTENT)
