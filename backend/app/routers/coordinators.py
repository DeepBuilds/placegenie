from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.deps import require_coordinator
from app.database.session import get_db
from app.models import User
from app.schemas.auth import UserOut
from app.schemas.coordinator import Analytics, CohortProgress, CoordinatorDashboard, StudentDetail, StudentPage
from app.schemas.report import CoordinatorReport
from app.services import coordinator_service, report_service, reporting_service
from app.schemas.ids import PathId, QueryId

# Every route here is coordinator-only. Students get 403; visitors who are not logged in get 401.
router = APIRouter(prefix="/coordinators", tags=["Coordinators"], dependencies=[Depends(require_coordinator)])


@router.get("/me", response_model=UserOut)
def coordinator_me(user: User = Depends(require_coordinator)):
    return user


@router.get("/dashboard", response_model=CoordinatorDashboard)
def dashboard(db: Session = Depends(get_db)):
    """Headline numbers for the placement cell, computed fresh from the database."""
    return coordinator_service.build_dashboard(db)


@router.get("/students", response_model=StudentPage)
def list_students(
    q: str | None = Query(default=None, max_length=100, description="Name, email or college"),
    branch_id: QueryId = None,
    year: int | None = Query(default=None, ge=1, le=6),
    min_cgpa: float | None = Query(default=None, ge=0, le=10),
    stage: Literal["placed", "in_process", "applied", "rejected", "not_applied"] | None = None,
    has_resume: bool | None = None,
    profile_ready: bool | None = Query(default=None, description="Profile at least 80% complete"),
    sort: Literal["name", "cgpa", "profile", "applications", "newest"] = "name",
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Search and filter the student list."""
    return coordinator_service.list_students(
        db, q=q, branch_id=branch_id, year=year, min_cgpa=min_cgpa, stage=stage, has_resume=has_resume,
        profile_ready=profile_ready, sort=sort, limit=limit, offset=offset,
    )


@router.get("/students/{student_id}", response_model=StudentDetail)
def student_detail(student_id: PathId, db: Session = Depends(get_db)):
    """One student's placement profile: profile, resume, progress, skill gaps, applications and interviews."""
    return coordinator_service.student_detail(db, student_id)


@router.get("/progress", response_model=CohortProgress)
def progress(db: Session = Depends(get_db)):
    """How far the whole cohort has got (same milestones as each student's own tracker)."""
    return coordinator_service.build_progress(db)


@router.get("/analytics", response_model=Analytics)
def analytics(db: Session = Depends(get_db)):
    return coordinator_service.build_analytics(db)


@router.get("/report", response_model=CoordinatorReport)
def placement_report(db: Session = Depends(get_db)):
    """The placement cell's report: placement statistics, company-wise and job-wise applications, selected students, skill gaps and progress."""
    return reporting_service.coordinator_report(db)


@router.get("/reports")
def list_reports():
    """The reports that can be downloaded."""
    return [{"kind": kind, "description": description, "url": f"/coordinators/reports/{kind}.csv"} for kind, description in report_service.REPORTS.items()]


@router.get("/reports/{kind}.csv")
def download_report(kind: str, db: Session = Depends(get_db)):
    filename, content = report_service.build_report(db, kind)
    return Response(
        content=content, media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )
