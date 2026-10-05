from typing import Literal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_coordinator, require_student
from app.database.session import get_db
from app.models import JobStatus, JobType, User
from app.repositories import job_repository as repo
from app.schemas.eligibility import EligibilityOut
from app.schemas.job import JobIn, JobOut, JobPage
from app.services import eligibility_service
from app.services import job_service as svc

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=JobPage)
def search_jobs(
    q: str | None = Query(default=None, max_length=100, description="Search title, description, company or skill"),
    company_id: int | None = None,
    job_type: JobType | None = None,
    role_id: int | None = None,
    skill_id: int | None = None,
    branch_id: int | None = Query(default=None, description="Jobs open to this branch"),
    location: str | None = Query(default=None, max_length=100),
    max_min_cgpa: float | None = Query(default=None, ge=0, le=10, description="Jobs whose minimum CGPA is at most this"),
    hide_expired: bool = False,
    status_filter: JobStatus | None = Query(default=None, alias="status", description="Coordinators only; students always see open jobs"),
    sort: Literal["newest", "deadline", "cgpa_low", "title"] = "newest",
    limit: int = Query(default=12, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search and filter jobs. Students only ever see open jobs; coordinators see all (optionally by status)."""
    filters = repo.JobFilters(
        q=q, company_id=company_id, job_type=job_type, role_id=role_id, skill_id=skill_id,
        branch_id=branch_id, location=location, max_min_cgpa=max_min_cgpa,
        hide_expired=hide_expired, status=status_filter, sort=sort,
    )
    return svc.search_jobs(db, user, filters, limit, offset)


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.get_job_for(db, job_id, user)


@router.post("/{job_id}/eligibility", response_model=EligibilityOut)
def check_eligibility(job_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    """Rule-based check of the logged-in student's profile against this job's requirements.

    Nothing is stored: the result is computed from the current profile every time.
    """
    return eligibility_service.check_for_student(db, user, job_id)


# ----- coordinator only -----
@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(data: JobIn, _: User = Depends(require_coordinator), db: Session = Depends(get_db)):
    return svc.create_job(db, data)


@router.put("/{job_id}", response_model=JobOut)
def update_job(job_id: int, data: JobIn, _: User = Depends(require_coordinator), db: Session = Depends(get_db)):
    return svc.update_job(db, job_id, data)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, _: User = Depends(require_coordinator), db: Session = Depends(get_db)):
    svc.delete_job(db, job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
