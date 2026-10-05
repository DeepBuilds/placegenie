from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.session import get_db
from app.repositories import student_repository as repo
from app.schemas.profile import CategorizedOut, NamedOut

# Lookup lists used by forms. Any logged-in user may read them.
router = APIRouter(tags=["Reference data"], dependencies=[Depends(get_current_user)])


@router.get("/branches", response_model=list[NamedOut])
def list_branches(db: Session = Depends(get_db)):
    return repo.list_branches(db)


@router.get("/skills", response_model=list[CategorizedOut])
def list_skills(db: Session = Depends(get_db)):
    return repo.list_skills(db)


@router.get("/job-roles", response_model=list[CategorizedOut])
def list_job_roles(db: Session = Depends(get_db)):
    return repo.list_job_roles(db)
