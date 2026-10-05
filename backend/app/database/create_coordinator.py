"""Create a coordinator account (public registration only creates students).

Usage (from backend/):  python -m app.database.create_coordinator
The password is typed at a hidden prompt, so it never appears in code or shell history.
"""
import getpass
import sys

from pydantic import ValidationError

from app.core.security import hash_password
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.models import Role
from app.repositories import user_repository
from app.schemas.auth import RegisterRequest


def main() -> int:
    full_name = input("Full name: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password (min 8, letters + numbers): ")
    try:
        data = RegisterRequest(full_name=full_name, email=email, password=password)
    except ValidationError as exc:
        print("Invalid input:", "; ".join(e["msg"] for e in exc.errors()))
        return 1

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if user_repository.get_by_email(db, data.email):
            print("A user with this email already exists.")
            return 1
        user_repository.create_user_with_profile(
            db,
            email=data.email,
            password_hash=hash_password(data.password),
            role=Role.COORDINATOR,
            full_name=data.full_name,
        )
    print(f"Coordinator {data.email} created.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
