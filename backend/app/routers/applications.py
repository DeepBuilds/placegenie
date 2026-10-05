from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_coordinator, require_student
from app.database.session import get_db
from app.models import ApplicationStatus, User
from app.schemas.application import (
    ApplicationDetail,
    ApplicationList,
    ApplyRequest,
    InterviewCreate,
    InterviewOut,
    StatusUpdate,
)
from app.services import application_service as svc

router = APIRouter(prefix="/applications", tags=["Applications"])


# ----- student -----
@router.post("", response_model=ApplicationDetail, status_code=status.HTTP_201_CREATED)
def apply(data: ApplyRequest, user: User = Depends(require_student), db: Session = Depends(get_db)):
    """Apply for an open job. One application per student per job (409 if already applied)."""
    return svc.apply(db, user, data.job_id)


@router.get("/me", response_model=ApplicationList)
def my_applications(
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    job_id: int | None = None,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """The logged-in student's applications, newest first, with per-status counts."""
    return svc.list_mine(db, user, status_filter, job_id)


@router.post("/{application_id}/withdraw", response_model=ApplicationDetail)
def withdraw(application_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    """Withdraw your own application (not possible once it is selected or rejected)."""
    return svc.withdraw(db, user, application_id)


# ----- coordinator -----
@router.get("", response_model=ApplicationList)
def all_applications(
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    job_id: int | None = None,
    company_id: int | None = None,
    q: str | None = Query(default=None, max_length=100, description="Student name/email, job title or company"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    """Every student's applications (coordinators only)."""
    return svc.list_all(db, status_filter=status_filter, job_id=job_id, company_id=company_id, q=q, limit=limit, offset=offset)


@router.patch("/{application_id}/status", response_model=ApplicationDetail)
def update_status(application_id: int, data: StatusUpdate, _: User = Depends(require_coordinator), db: Session = Depends(get_db)):
    """Set the official application status (shortlisted, selected, ...). Coordinators only."""
    return svc.set_status(db, application_id, data.status)


# ----- both roles (a student only reaches their own) -----
@router.get("/{application_id}", response_model=ApplicationDetail)
def application_detail(application_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.get_detail(db, user, application_id)


@router.post("/{application_id}/interviews", response_model=InterviewOut, status_code=status.HTTP_201_CREATED)
def add_interview(application_id: int, data: InterviewCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Record an interview / test stage for an application."""
    return svc.add_interview(db, user, application_id, data)
