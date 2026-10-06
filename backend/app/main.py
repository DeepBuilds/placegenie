import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError

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
    reports,
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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # /jobs/abc or /jobs/0 names something that cannot exist: answer "not found" like any unknown id.
    errors = exc.errors()
    if errors and all(e.get("loc", ("",))[0] == "path" for e in errors):
        return JSONResponse(status_code=404, content={"detail": "Not found."})
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, exc: IntegrityError):
    # e.g. two identical requests at the same moment (double-click on Apply): the unique constraint wins
    logger.warning("Integrity error: %s", exc.orig)
    return JSONResponse(status_code=409, content={"detail": "This conflicts with data that already exists. Refresh the page and try again."})


@app.exception_handler(DataError)
async def data_error_handler(_: Request, exc: DataError):
    logger.warning("Data error: %s", exc.orig)
    return JSONResponse(status_code=422, content={"detail": "One of the values is not valid for the database."})


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_: Request, exc: SQLAlchemyError):
    logger.exception("Database error")
    return JSONResponse(
        status_code=503,
        content={"detail": "The database is temporarily unavailable. Please try again later."},
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exc: Exception):
    # Logged in full on the server; the client never sees a traceback or internal names.
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server. Please try again later."})


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
app.include_router(reports.router, prefix=API_PREFIX)
