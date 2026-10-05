from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_student
from app.database.session import get_db
from app.models import User
from app.schemas.recommendation import RecommendationPage
from app.services import recommendation_service

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("", response_model=RecommendationPage)
def get_recommendations(
    role_id: int | None = Query(default=None, description="Only jobs with this role"),
    location: str | None = Query(default=None, max_length=100, description="Only jobs whose location contains this text"),
    eligible_only: bool = Query(default=False, description="Hide jobs you are not (yet) eligible for"),
    sort: Literal["score_desc", "score_asc", "deadline", "title"] = "score_desc",
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """Open jobs ranked for the logged-in student with a transparent 0-100 match score.

    Computed on every request from the current profile; nothing is stored.
    """
    return recommendation_service.recommend_for(
        db,
        user,
        role_id=role_id,
        location=location,
        eligible_only=eligible_only,
        sort=sort,
        limit=limit,
        offset=offset,
    )
