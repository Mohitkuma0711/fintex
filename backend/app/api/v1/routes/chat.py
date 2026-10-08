import asyncio
import json
from collections.abc import AsyncIterator
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.v1.dependencies import get_chat_service
from app.core.auth import get_current_user
from app.models import ChatMessage, ChatSession, User
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionResponse,
    CreateChatSessionRequest,
)
from app.services.chat.service import ChatService, ChatServiceError

router = APIRouter(prefix="/chat", tags=["chat"])
logger = structlog.get_logger(__name__)


def _message_response(message: ChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse.model_validate(
        {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "citations": message.citations,
            "created_at": message.created_at,
        }
    )


def _session_response(chat_session: ChatSession) -> ChatSessionResponse:
    return ChatSessionResponse.model_validate(
        {
            "id": chat_session.id,
            "title": chat_session.title,
            "created_at": chat_session.created_at,
        }
    )


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    request: CreateChatSessionRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatSessionResponse:
    return _session_response(await service.create_session(request.title))


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_chat_sessions(
    service: ChatService = Depends(get_chat_service),
) -> list[ChatSessionResponse]:
    return [_session_response(row) for row in await service.list_sessions()]


@router.get("/sessions/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: UUID,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatHistoryResponse:
    history = await service.get_history(session_id)
    if history is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    chat_session, messages = history
    if chat_session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    return ChatHistoryResponse(
        session=_session_response(chat_session),
        messages=[_message_response(message) for message in messages],
    )


@router.post("/sessions/{session_id}/messages/stream")
async def stream_chat_message(
    session_id: UUID,
    request: ChatMessageRequest,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    history = await service.get_history(session_id)
    if history is None or history[0].user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")

    async def event_stream() -> AsyncIterator[str]:
        yield 'event: status\ndata: {"status":"thinking"}\n\n'
        try:
            assistant_message = await service.respond(session_id, request.content)
        except ChatServiceError as error:
            logger.warning("chat_stream_failed", error_type=type(error).__name__)
            yield (
                "event: error\ndata: "
                + json.dumps({"message": "The assistant could not complete this request safely."})
                + "\n\n"
            )
            return

        content = assistant_message.content
        for offset in range(0, len(content), 48):
            delta = content[offset : offset + 48]
            yield f"event: delta\ndata: {json.dumps({'text': delta}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)
        yield (
            "event: citations\ndata: "
            + json.dumps(assistant_message.citations, ensure_ascii=False, default=str)
            + "\n\n"
        )
        yield (
            "event: done\ndata: " + json.dumps({"message_id": str(assistant_message.id)}) + "\n\n"
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
