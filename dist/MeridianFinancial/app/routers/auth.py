from __future__ import annotations

from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.security import SESSION_COOKIE, create_session_token
from app.routers.deps import CurrentUser, DbSession
from app.services.auth import AuthError, AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    display_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileResponse(BaseModel):
    id: int
    display_name: str
    email: str


def _set_session_cookie(response: Response, user_id: int) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user_id),
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
    )


@router.get("/profiles", response_model=list[ProfileResponse])
async def list_profiles(session: DbSession):
    """Profiles for the welcome screen. Names only — all data behind each requires login."""
    return await AuthService(session).list_profiles()


@router.post("/register", response_model=ProfileResponse, status_code=201)
async def register(body: RegisterRequest, response: Response, session: DbSession):
    profile = await AuthService(session).register(body.display_name, body.email, body.password)
    _set_session_cookie(response, profile.id)
    return profile


@router.post("/login", response_model=ProfileResponse)
async def login(body: LoginRequest, response: Response, session: DbSession):
    profile = await AuthService(session).login(body.email, body.password)
    _set_session_cookie(response, profile.id)
    return profile


@router.post("/logout", status_code=204)
async def logout(response: Response, session: DbSession, user: CurrentUser):
    await AuthService(session).logout(user.id)
    response.delete_cookie(SESSION_COOKIE)


@router.get("/me", response_model=ProfileResponse)
async def me(user: CurrentUser):
    return user
