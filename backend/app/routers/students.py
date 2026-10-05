from fastapi import APIRouter, Depends

from app.core.deps import require_student
from app.models import User
from app.schemas.auth import UserOut

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/me", response_model=UserOut)
def student_me(user: User = Depends(require_student)):
    """Student-only. The full profile (Phase 4) will be served from here."""
    return user
