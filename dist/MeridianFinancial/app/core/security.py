"""Password hashing (Argon2id) and session tokens (JWT)."""
from __future__ import annotations

import datetime as dt

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.core.config import get_settings

MIN_PASSWORD_LENGTH = 10

_hasher = PasswordHasher()  # argon2id by default

SESSION_COOKIE = "meridian_session"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerificationError:
        return False


def validate_password_strength(password: str) -> str | None:
    """Return a plain-language problem with the password, or None if acceptable."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    return None


def create_session_token(user_id: int) -> str:
    settings = get_settings()
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + dt.timedelta(hours=settings.session_hours),
    }
    return jwt.encode(payload, settings.resolve_jwt_secret(), algorithm="HS256")


def decode_session_token(token: str) -> int | None:
    """Return the user id the token asserts, or None if invalid/expired."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.resolve_jwt_secret(), algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
