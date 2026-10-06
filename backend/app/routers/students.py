from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_student
from app.database.session import get_db
from app.models import Student, User
from app.schemas.profile import (
    CertificationIn,
    ExperienceIn,
    PreferencesUpdate,
    ProfileOut,
    ProfileUpdate,
    ProjectIn,
    SkillsUpdate,
)
from app.services import profile_service as svc
from app.schemas.ids import PathId

router = APIRouter(prefix="/students/me", tags=["Student profile"])


def current_student(user: User = Depends(require_student), db: Session = Depends(get_db)) -> Student:
    return svc.get_student(db, user)


@router.get("", response_model=ProfileOut)
def get_profile(student: Student = Depends(current_student)):
    """Full profile of the logged-in student, including completeness."""
    return svc.to_profile_out(student)


@router.put("", response_model=ProfileOut)
def update_profile(
    data: ProfileUpdate, student: Student = Depends(current_student), db: Session = Depends(get_db)
):
    """Replace basic and academic details."""
    return svc.update_basic(db, student, data)


@router.put("/skills", response_model=ProfileOut)
def replace_skills(
    data: SkillsUpdate, student: Student = Depends(current_student), db: Session = Depends(get_db)
):
    """Replace the student's whole skill list (ids come from GET /skills)."""
    return svc.replace_skills(db, student, data)


@router.put("/preferences", response_model=ProfileOut)
def update_preferences(
    data: PreferencesUpdate, student: Student = Depends(current_student), db: Session = Depends(get_db)
):
    return svc.update_preferences(db, student, data)


# ----- certifications -----
@router.post("/certifications", response_model=ProfileOut, status_code=201)
def add_certification(data: CertificationIn, student: Student = Depends(current_student), db: Session = Depends(get_db)):
    return svc.add_item(db, student, "certifications", data)


@router.put("/certifications/{item_id}", response_model=ProfileOut)
def update_certification(item_id: PathId, data: CertificationIn, student: Student = Depends(current_student), db: Session = Depends(get_db)):
    return svc.update_item(db, student, "certifications", item_id, data)


@router.delete("/certifications/{item_id}", response_model=ProfileOut)
def delete_certification(item_id: PathId, student: Student = Depends(current_student), db: Session = Depends(get_db)):
    return svc.delete_item(db, student, "certifications", item_id)


# ----- projects -----
@router.post("/projects", response_model=ProfileOut, status_code=201)
def add_project(data: ProjectIn, student: Student = Depends(current_student), db: Session = Depends(get_db)):
    return svc.add_item(db, student, "projects", data)


@router.put("/projects/{item_id}", response_model=ProfileOut)
def update_project(item_id: PathId, data: ProjectIn, student: Student = Depends(current_student), db: Session = Depends(get_db)):
    return svc.update_item(db, student, "projects", item_id, data)


@router.delete("/projects/{item_id}", response_model=ProfileOut)
def delete_project(item_id: PathId, student: Student = Depends(current_student), db: Session = Depends(get_db)):
    return svc.delete_item(db, student, "projects", item_id)


# ----- experiences -----
@router.post("/experiences", response_model=ProfileOut, status_code=201)
def add_experience(data: ExperienceIn, student: Student = Depends(current_student), db: Session = Depends(get_db)):
    return svc.add_item(db, student, "experiences", data)


@router.put("/experiences/{item_id}", response_model=ProfileOut)
def update_experience(item_id: PathId, data: ExperienceIn, student: Student = Depends(current_student), db: Session = Depends(get_db)):
    return svc.update_item(db, student, "experiences", item_id, data)


@router.delete("/experiences/{item_id}", response_model=ProfileOut)
def delete_experience(item_id: PathId, student: Student = Depends(current_student), db: Session = Depends(get_db)):
    return svc.delete_item(db, student, "experiences", item_id)
