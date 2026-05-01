"""POST /api/chat — wraps the existing Coordinator pipeline.

The Coordinator and all downstream agents/tools are unchanged. This route
just translates an HTTP request into a `coordinator.process()` call and
returns the existing Adaptive Card JSON the Teams bot used to render.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.middleware.easy_auth import AuthenticatedUser, get_authenticated_user
from src.bot.adaptive_cards import build_error_card
from src.bot.turn_state import get_state
from src.orchestrator.coordinator import Coordinator

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# Coordinator is cheap to construct (just reads env vars) but we cache one
# instance per process so we don't re-read env on every request.
_coordinator: Coordinator | None = None


def _get_coordinator() -> Coordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = Coordinator()
    return _coordinator


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = Field(
        default=None,
        description="Stable conversation id from the client; one is generated if absent.",
    )


class ChatResponse(BaseModel):
    card: dict
    dax: str
    summary: str
    data: list[dict] = []
    conversation_id: str
    user: str


def _user_dependency(request: Request) -> AuthenticatedUser:
    return get_authenticated_user(request)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    user: AuthenticatedUser = Depends(_user_dependency),
) -> ChatResponse:
    if not user.upn:
        raise HTTPException(
            status_code=401,
            detail="No authenticated user. Easy Auth header missing and LOCAL_DEV_UPN not set.",
        )

    conversation_id = payload.conversation_id or str(uuid.uuid4())
    state = get_state(conversation_id)
    state.new_turn(payload.question)

    coordinator = _get_coordinator()

    logger.info(
        "chat_request",
        upn=user.upn,
        conversation_id=conversation_id,
        question_preview=payload.question[:120],
        is_local_dev=user.is_local_dev,
    )

    try:
        result = await coordinator.process(
            user_question=payload.question,
            state=state,
            user_principal_name=user.upn,
        )
    except Exception as exc:  # noqa: BLE001 — surface as Adaptive Card, never 500 to the UI
        logger.exception("coordinator_failed", error=str(exc))
        return ChatResponse(
            card=build_error_card(
                "The agent pipeline failed unexpectedly. Please try again or contact the Cx Insights team."
            ),
            dax="",
            summary="",
            data=[],
            conversation_id=conversation_id,
            user=user.upn,
        )

    return ChatResponse(
        card=result["card"],
        dax=result.get("dax", ""),
        summary=result.get("summary", ""),
        data=result.get("data", []),
        conversation_id=conversation_id,
        user=user.upn,
    )
