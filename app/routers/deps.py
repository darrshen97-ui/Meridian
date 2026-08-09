"""Request dependencies: database session and the authenticated user."""
from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import SESSION_COOKIE, decode_session_token
from app.domain.models import UserProfile
from app.repositories.users import UserRepository

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    session: DbSession,
    meridian_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> UserProfile:
    if not meridian_session:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    user_id = decode_session_token(meridian_session)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
    profile = await UserRepository(session).get_by_id(user_id)
    if profile is None:
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
    return profile


CurrentUser = Annotated[UserProfile, Depends(get_current_user)]
