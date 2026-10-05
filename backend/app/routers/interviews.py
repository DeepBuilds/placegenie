from typing import Literal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_coordinator, require_student
from app.database.session import get_db
from app.models import User
from app.schemas.application import InterviewList, InterviewListItem, InterviewOut, InterviewUpdate
from app.services import application_service as svc

router = APIRouter(prefix="/interviews", tags=["Interviews"])

When = Literal["upcoming", "past", "unscheduled", "all"]


@router.get("/me", response_model=InterviewList)
def my_interviews(when: When = "all", user: User = Depends(require_student), db: Session = Depends(get_db)):
    """The logged-in student's interviews: upcoming (soonest first), past (latest first) or unscheduled."""
    return svc.list_interviews(db, user, when)


@router.get("", response_model=InterviewList)
def all_interviews(when: When = "all", user: User = Depends(require_coordinator), db: Session = Depends(get_db)):
    """Every student's interviews (coordinators only)."""
    return svc.list_interviews(db, user, when)


@router.get("/{interview_id}", response_model=InterviewListItem)
def interview_detail(interview_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.get_interview_detail(db, user, interview_id)


@router.patch("/{interview_id}", response_model=InterviewOut)
def update_interview(interview_id: int, data: InterviewUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Change the stage, date/time, notes or result. Only the fields you send are changed."""
    return svc.update_interview(db, user, interview_id, data)


@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interview(interview_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc.delete_interview(db, user, interview_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
