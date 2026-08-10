"""User repository.

This is the ONLY repository allowed methods without a `user_id` parameter, because
authentication (email lookup) and the pre-auth profile list are inherently
pre-identity. Every other repository is user-scoped on every method — enforced by
tests/test_repo_signatures.py.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import ProfileSummary, UserProfile
from app.models import User


def _to_profile(u: User) -> UserProfile:
    return UserProfile(
        id=u.id,
        display_name=u.display_name,
        email=u.email,
        created_at=u.created_at,
        last_login_at=u.last_login_at,
    )


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, display_name: str, email: str, password_hash: str) -> UserProfile:
        user = User(display_name=display_name, email=email, password_hash=password_hash)
        self.session.add(user)
        await self.session.flush()
        return _to_profile(user)

    async def get_by_email_with_hash(self, email: str) -> tuple[UserProfile, str] | None:
        row = await self.session.scalar(select(User).where(User.email == email.lower()))
        if row is None:
            return None
        return _to_profile(row), row.password_hash

    async def get_by_id(self, user_id: int) -> UserProfile | None:
        row = await self.session.get(User, user_id)
        return _to_profile(row) if row else None

    async def list_profiles(self) -> list[ProfileSummary]:
        rows = await self.session.scalars(select(User).order_by(User.display_name))
        return [ProfileSummary(id=u.id, display_name=u.display_name, email=u.email) for u in rows]

    async def touch_last_login(self, user_id: int, when) -> None:
        row = await self.session.get(User, user_id)
        if row is not None:
            row.last_login_at = when
