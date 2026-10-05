from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_coordinator
from app.database.session import get_db
from app.models import User
from app.repositories import job_repository as repo
from app.schemas.job import CompanyIn, CompanyOut, JobPage
from app.services import job_service as svc

router = APIRouter(prefix="/companies", tags=["Companies"])


class CompanyPage(BaseModel):
    items: list[CompanyOut]
    total: int
    limit: int
    offset: int


@router.get("", response_model=CompanyPage)
def list_companies(
    q: str | None = Query(default=None, max_length=100, description="Search name or industry"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows, total = repo.list_companies(db, q, limit, offset)
    return CompanyPage(
        items=[svc.to_company_out(c, n) for c, n in rows], total=total, limit=limit, offset=offset
    )


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    company = svc.get_company_or_404(db, company_id)
    return svc.to_company_out(company, repo.count_open_jobs(db, company_id))


@router.get("/{company_id}/jobs", response_model=JobPage)
def jobs_of_company(
    company_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc.get_company_or_404(db, company_id)
    return svc.search_jobs(db, user, repo.JobFilters(company_id=company_id), limit, offset)


# ----- coordinator only -----
@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(data: CompanyIn, _: User = Depends(require_coordinator), db: Session = Depends(get_db)):
    return svc.create_company(db, data)


@router.put("/{company_id}", response_model=CompanyOut)
def update_company(company_id: int, data: CompanyIn, _: User = Depends(require_coordinator), db: Session = Depends(get_db)):
    return svc.update_company(db, company_id, data)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(company_id: int, _: User = Depends(require_coordinator), db: Session = Depends(get_db)):
    svc.delete_company(db, company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
