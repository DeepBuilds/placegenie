from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Liveness + database connectivity check.

    The API itself is "ok" even if MySQL is down; the database block reports
    that separately so the problem is visible instead of a generic 500.
    """
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database = {"connected": True, "detail": "ok"}
    except SQLAlchemyError:
        database = {
            "connected": False,
            "detail": "Cannot connect to MySQL. Check DB_* values in backend/.env.",
        }
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "database": database,
    }
