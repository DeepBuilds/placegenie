from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

MIN_SECRET_LENGTH = 32


class TokenError(Exception):
    """Raised for invalid tokens; `expired` allows a clearer message for expiry."""

    def __init__(self, message: str, expired: bool = False):
        super().__init__(message)
        self.expired = expired


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# Used to spend the same time when an email is unknown, so login timing
# does not reveal which emails are registered.
DUMMY_HASH = hash_password("not-a-real-password")


def _secret() -> str:
    secret = get_settings().jwt_secret_key
    if len(secret) < MIN_SECRET_LENGTH or secret.startswith("replace_with"):
        raise RuntimeError(
            "JWT_SECRET_KEY is missing or too weak. Set a random value of at least "
            f"{MIN_SECRET_LENGTH} characters in backend/.env."
        )
    return secret


def create_access_token(user_id: int, role: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, _secret(), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            _secret(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Session expired. Please log in again.", expired=True) from exc
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid authentication token.") from exc
