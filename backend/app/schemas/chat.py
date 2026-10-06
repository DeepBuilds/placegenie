from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models import ChatRole
from app.schemas.ids import BodyId


class ChatRequest(BaseModel):
    # Length and emptiness are checked in the service so the student gets a friendly message.
    message: str = Field(max_length=20000)
    conversation_id: BodyId | None = None


class MessageOut(BaseModel):
    id: int
    role: ChatRole
    content: str
    source: str | None  # how an assistant reply was produced; null for the student's own messages
    created_at: datetime


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class ChatReplyOut(BaseModel):
    conversation: ConversationOut
    user_message: MessageOut
    reply: MessageOut
    suggestions: list[str]  # follow-up questions the UI can offer as buttons


class ChatInfo(BaseModel):
    mode: Literal["ai", "guide"]  # "ai" = a language model answers general questions; "guide" = the built-in guide
    provider: str | None
    max_message_chars: int
    starters: list[str]
    disclaimer: str
