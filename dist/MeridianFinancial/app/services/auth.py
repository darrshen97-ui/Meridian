"""Authentication and profile service."""
from __future__ import annotations

import datetime as dt
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.domain.models import ProfileSummary, UserProfile
from app.repositories.audit import AuditRepository
from app.repositories.users import UserRepository


class AuthError(Exception):
    """A problem the user can act on; message is safe to show."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# Brute-force protection. Found by the milestone-16 security audit: nothing stopped
# unlimited password guesses against a known demo email. In-process state is the
# right scope for a single-user local app (D-026).
MAX_ATTEMPTS = 8
LOCKOUT_SECONDS = 300
_failures: dict[str, list[float]] = {}


def _recent_failures(email: str) -> list[float]:
    now = time.monotonic()
    kept = [t for t in _failures.get(email, []) if now - t < LOCKOUT_SECONDS]
    _failures[email] = kept
    return kept


def _record_failure(email: str) -> None:
    _failures.setdefault(email, []).append(time.monotonic())


def reset_login_throttle() -> None:
    """Testing hook."""
    _failures.clear()


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.audit = AuditRepository(session)

    async def register(self, display_name: str, email: str, password: str) -> UserProfile:
        display_name = display_name.strip()
        email = email.strip().lower()
        if not display_name:
            raise AuthError("Display name is required.")
        if "@" not in email or "." not in email.split("@")[-1]:
            raise AuthError("Enter a valid email address.")
        problem = validate_password_strength(password)
        if problem:
            raise AuthError(problem)
        if await self.users.get_by_email_with_hash(email) is not None:
            raise AuthError("A profile with this email already exists.", status_code=409)

        profile = await self.users.create(display_name, email, hash_password(password))
        await self.audit.append(profile.id, event="profile.created",
                                detail={"email": email})
        await self.session.commit()
        return profile

    async def login(self, email: str, password: str) -> UserProfile:
        email = email.strip().lower()
        if len(_recent_failures(email)) >= MAX_ATTEMPTS:
            raise AuthError(
                "Too many failed sign-in attempts. Wait five minutes and try again.",
                status_code=429)

        found = await self.users.get_by_email_with_hash(email)
        if found is None:
            _record_failure(email)
            raise AuthError("Email or password is incorrect.", status_code=401)
        profile, password_hash = found
        if not verify_password(password_hash, password):
            _record_failure(email)
            await self.audit.append(profile.id, event="login.failed")
            await self.session.commit()
            raise AuthError("Email or password is incorrect.", status_code=401)
        _failures.pop(email, None)

        now = dt.datetime.now(dt.timezone.utc)
        await self.users.touch_last_login(profile.id, now)
        await self.audit.append(profile.id, event="login.succeeded")
        await self.session.commit()
        return profile

    async def logout(self, user_id: int) -> None:
        await self.audit.append(user_id, event="logout")
        await self.session.commit()

    async def get_profile(self, user_id: int) -> UserProfile | None:
        return await self.users.get_by_id(user_id)

    async def list_profiles(self) -> list[ProfileSummary]:
        return await self.users.list_profiles()
