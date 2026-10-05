from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.deps import require_student
from app.database.session import get_db
from app.models import User
from app.schemas.report import StudentReport
from app.services import report_service, reporting_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/me", response_model=StudentReport)
def my_report(user: User = Depends(require_student), db: Session = Depends(get_db)):
    """The logged-in student's own report: applications, statuses, interviews, outcome, recommended jobs, skill gaps and progress."""
    return reporting_service.student_report(db, user)


@router.get("/me.csv")
def my_report_csv(user: User = Depends(require_student), db: Session = Depends(get_db)):
    filename, content = report_service.build_student_csv(reporting_service.student_report(db, user, light=True))
    return Response(
        content=content, media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )
