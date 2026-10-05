from fastapi import APIRouter, Depends

from app.core.deps import require_coordinator
from app.models import User
from app.schemas.auth import UserOut

router = APIRouter(prefix="/coordinators", tags=["Coordinators"])


@router.get("/me", response_model=UserOut)
def coordinator_me(user: User = Depends(require_coordinator)):
    """Coordinator-only."""
    return user
