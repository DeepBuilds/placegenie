from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import require_student
from app.database.session import get_db
from app.models import User
from app.schemas.resume import ResumeAnalysisOut, ResumeOut
from app.services import resume_service
from app.schemas.ids import PathId

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.post("", response_model=ResumeAnalysisOut, status_code=status.HTTP_201_CREATED)
def upload_resume(
    file: UploadFile = File(..., description="A text-based PDF resume (max size set by RESUME_MAX_MB)"),
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """Upload a PDF resume. It is validated, analysed and stored; it replaces any earlier resume."""
    resume_service.validate_upload_meta(file.filename, file.content_type)
    # Read at most one byte more than the limit so an oversized file is detected without loading all of it.
    data = file.file.read(get_settings().resume_max_bytes + 1)
    return resume_service.upload_resume(db, user, file.filename, file.content_type, data)


@router.get("/me", response_model=ResumeOut | None)
def my_resume(user: User = Depends(require_student), db: Session = Depends(get_db)):
    """The logged-in student's current resume, or null if none was uploaded."""
    return resume_service.current_resume(db, user)


@router.get("/{resume_id}/analysis", response_model=ResumeAnalysisOut)
def resume_analysis(resume_id: PathId, user: User = Depends(require_student), db: Session = Depends(get_db)):
    return resume_service.get_analysis(db, user, resume_id)


@router.post("/{resume_id}/analyze", response_model=ResumeAnalysisOut)
def reanalyze_resume(resume_id: PathId, user: User = Depends(require_student), db: Session = Depends(get_db)):
    """Re-run the analysis on the stored text (no new upload needed)."""
    return resume_service.reanalyze(db, user, resume_id)


@router.post("/{resume_id}/sync-skills", response_model=ResumeAnalysisOut)
def sync_skills(resume_id: PathId, user: User = Depends(require_student), db: Session = Depends(get_db)):
    """Add the skills detected in this resume to the student's own profile."""
    return resume_service.sync_skills(db, user, resume_id)


@router.get("/{resume_id}/file")
def download_resume(resume_id: PathId, user: User = Depends(require_student), db: Session = Depends(get_db)):
    """Download the student's own PDF."""
    path, name = resume_service.file_for_download(db, user, resume_id)
    return FileResponse(
        path, media_type="application/pdf", filename=name,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(resume_id: PathId, user: User = Depends(require_student), db: Session = Depends(get_db)):
    resume_service.delete_resume(db, user, resume_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
