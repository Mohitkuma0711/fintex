from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class ChatApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citation(ChatApiModel):
    source: str
    section: str
    link: AnyHttpUrl


class CreateChatSessionRequest(ChatApiModel):
    title: str | None = Field(default=None, max_length=200)


class ChatSessionResponse(ChatApiModel):
    id: UUID
    title: str | None
    created_at: datetime


class ChatMessageRequest(ChatApiModel):
    content: str = Field(min_length=1, max_length=4_000)


class ChatMessageResponse(ChatApiModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    citations: list[Citation]
    created_at: datetime


class ChatHistoryResponse(ChatApiModel):
    session: ChatSessionResponse
    messages: list[ChatMessageResponse]
