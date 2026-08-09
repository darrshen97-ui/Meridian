"""AI, categorization, review-queue, and audit endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.providers.llm import LLMError, LLMUnavailable, reset_llm_provider
from app.repositories.audit import AuditRepository
from app.routers.deps import CurrentUser, DbSession
from app.services.ai import AIService
from app.services.app_settings import write_app_settings
from app.services.categorization import CategorizationService
from app.services.review import ReviewService

router = APIRouter(prefix="/api", tags=["ai"])

KNOWN_MODELS = ["qwen2.5:7b-instruct", "qwen2.5:3b-instruct"]


def register_exception_handler(app) -> None:
    @app.exception_handler(LLMUnavailable)
    async def handle_unavailable(request: Request, exc: LLMUnavailable):
        return JSONResponse(status_code=503, content={"detail": exc.message})

    @app.exception_handler(LLMError)
    async def handle_llm_error(request: Request, exc: LLMError):
        return JSONResponse(status_code=502, content={"detail": exc.message})


@router.get("/ai/status")
async def ai_status(session: DbSession, user: CurrentUser):
    return await AIService(session).status(user.id)


@router.post("/ai/selftest")
async def ai_selftest(session: DbSession, user: CurrentUser):
    return await AIService(session).selftest(user.id)


class ModelChoice(BaseModel):
    model: str


@router.put("/ai/model")
async def choose_model(body: ModelChoice, session: DbSession, user: CurrentUser):
    if body.model not in KNOWN_MODELS:
        return JSONResponse(status_code=422, content={
            "detail": f"Choose one of: {', '.join(KNOWN_MODELS)}"})
    write_app_settings({"ollama_model": body.model})
    reset_llm_provider()
    await AuditRepository(session).append(user.id, event="settings.model_changed",
                                          detail={"model": body.model})
    await session.commit()
    return {"model": body.model}


class CategorizeRequest(BaseModel):
    limit: int = Field(default=500, ge=1, le=5000)


@router.post("/categorize/run")
async def categorize_run(body: CategorizeRequest, session: DbSession,
                         user: CurrentUser):
    return await CategorizationService(session).run(user.id, limit=body.limit)


@router.get("/review")
async def review_queue(session: DbSession, user: CurrentUser, limit: int = 100):
    return await ReviewService(session).queue(user.id, limit=min(limit, 500))


class ResolveRequest(BaseModel):
    category_id: int
    apply_to_matching: bool = False


@router.post("/review/{transaction_id}/resolve")
async def review_resolve(transaction_id: int, body: ResolveRequest,
                         session: DbSession, user: CurrentUser):
    return await ReviewService(session).resolve(
        user.id, transaction_id, category_id=body.category_id,
        apply_to_matching=body.apply_to_matching)


@router.get("/audit")
async def audit_log(session: DbSession, user: CurrentUser, limit: int = 50):
    return await AuditRepository(session).list(user.id, limit=min(limit, 200))
