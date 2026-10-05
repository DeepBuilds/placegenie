import os

# Must be set before the app is imported: tests never use the real .env secrets/DB.
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-jwt-123456"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models import Role
from app.repositories import user_repository

STUDENT = {"full_name": "Asha Patil", "email": "asha@example.com", "password": "Passw0rd123"}
COORDINATOR = {"full_name": "Dr. Rao", "email": "rao@example.com", "password": "Coordin8tor1"}


@pytest.fixture
def db_session():
    """Fresh in-memory SQLite database per test (fast, isolated)."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    # SQLite ignores foreign keys unless asked; MySQL always enforces them.
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def coordinator(db_session):
    """Coordinators cannot self-register, so create one directly."""
    return user_repository.create_user_with_profile(
        db_session,
        email=COORDINATOR["email"],
        password_hash=hash_password(COORDINATOR["password"]),
        role=Role.COORDINATOR,
        full_name=COORDINATOR["full_name"],
    )


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def student_token(client):
    return client.post("/api/v1/auth/register", json=STUDENT).json()["access_token"]


@pytest.fixture
def coordinator_token(client, coordinator):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": COORDINATOR["email"], "password": COORDINATOR["password"]},
    )
    return res.json()["access_token"]
