"""Coach endpoint. Conversation history is session-scoped client-side (D-005)."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.routers.deps import CurrentUser, DbSession
from app.services.coach import CoachService

router = APIRouter(prefix="/api/coach", tags=["coach"])


class HistoryItem(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    history: list[HistoryItem] = Field(default_factory=list, max_length=12)


@router.post("/ask")
async def ask(body: AskRequest, session: DbSession, user: CurrentUser):
    return await CoachService(session).ask(
        user.id, body.question,
        history=[h.model_dump() for h in body.history])
