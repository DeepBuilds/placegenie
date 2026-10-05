import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.core.config import get_settings
from app.database.base import Base
from app.database.seed import seed_reference_data
from app.database.session import SessionLocal, engine
from app.routers import (
    applications,
    auth,
    chat,
    companies,
    coordinators,
    dashboard,
    health,
    interviews,
    jobs,
    recommendations,
    reference,
    resumes,
    students,
)

settings = get_settings()
logger = logging.getLogger("placegenie")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Create missing tables. Phase 2 will replace this with the full schema.
    try:
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            seed_reference_data(db)  # inserts only missing lookup rows
    except SQLAlchemyError:
        logger.warning("Could not reach MySQL at startup; check DB_* values in backend/.env.")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Intelligent placement assistant API. Guidance only; not a recruitment decision-maker.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    """Refuse an obviously oversized resume upload before the body is read (Content-Length check)."""
    if request.method == "POST" and request.url.path.rstrip("/").endswith("/resumes"):
        declared = request.headers.get("content-length")
        limit = settings.resume_max_bytes + 64 * 1024  # room for the multipart envelope
        if declared and declared.isdigit() and int(declared) > limit:
            return JSONResponse(
                status_code=413,
                content={"detail": f"The file is too large. The maximum size is {settings.resume_max_mb} MB."},
            )
    return await call_next(request)


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_: Request, exc: SQLAlchemyError):
    logger.exception("Database error")
    return JSONResponse(
        status_code=503,
        content={"detail": "The database is temporarily unavailable. Please try again later."},
    )


API_PREFIX = "/api/v1"
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(students.router, prefix=API_PREFIX)
app.include_router(coordinators.router, prefix=API_PREFIX)
app.include_router(reference.router, prefix=API_PREFIX)
app.include_router(companies.router, prefix=API_PREFIX)
app.include_router(jobs.router, prefix=API_PREFIX)
app.include_router(recommendations.router, prefix=API_PREFIX)
app.include_router(resumes.router, prefix=API_PREFIX)
app.include_router(applications.router, prefix=API_PREFIX)
app.include_router(interviews.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
