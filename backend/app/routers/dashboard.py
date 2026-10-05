from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_student
from app.database.session import get_db
from app.models import User
from app.schemas.dashboard import DashboardOut
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardOut)
def student_dashboard(user: User = Depends(require_student), db: Session = Depends(get_db)):
    """Everything the student's home page shows, composed from the existing modules.

    Read-only and computed fresh on every request. If one section fails it is returned as null with a
    message in `errors`, and the other sections are unaffected.
    """
    return dashboard_service.build_dashboard(db, user)
