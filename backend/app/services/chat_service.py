"""Conversations: validation, rate limiting, history and saving. The answering itself is in chatbot_engine.

What is stored: the student's messages and the assistant's replies, each with a timestamp (and, for
replies, how they were produced). Nothing else: no prompts, no profile snapshots, no model payloads,
no IP addresses. A student can delete one conversation or all of them at any time.
"""
import re
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.chatbot.providers import ChatTurn
from app.core.config import get_settings
from app.models import ChatConversation, ChatMessage, ChatRole, User
from app.repositories import chat_repository as repo
from app.schemas.chat import ChatInfo, ChatReplyOut, ConversationDetail, ConversationOut, MessageOut
from app.services import profile_service
from app.services.chatbot_engine import STARTERS, ChatbotEngine

DISCLAIMER = (
    "PlaceGenie gives guidance only. It has no live information about companies, hiring decisions or schedules. "
    "AI-written answers can be wrong: check important details with your placement cell."
)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


def _error(code: int, detail: str, headers: dict | None = None) -> HTTPException:
    return HTTPException(code, detail, headers=headers)


# ---------- helpers ----------
def clean_message(raw: str) -> str:
    text = _CONTROL.sub("", raw).replace("\r\n", "\n").strip()
    limit = get_settings().chat_max_message_chars
    if not text:
        raise _error(422, "Please type a message.")
    if len(text) > limit:
        raise _error(422, f"Messages can be at most {limit} characters. Yours has {len(text)}.")
    return text


def make_title(first_message: str) -> str:
    title = " ".join(first_message.split())[:60].rstrip(" .,;:!?-")
    return title or "New chat"


def to_message_out(m: ChatMessage) -> MessageOut:
    return MessageOut(id=m.id, role=m.role, content=m.content, source=m.source, created_at=m.created_at)


def to_conversation_out(c: ChatConversation, count: int) -> ConversationOut:
    return ConversationOut(id=c.id, title=c.title, created_at=c.created_at, updated_at=c.updated_at, message_count=count)


def check_rate_limit(db: Session, student_id: int) -> None:
    limit = get_settings().chat_rate_limit_per_minute
    sent = repo.user_messages_since(db, student_id, _now() - timedelta(seconds=60))
    if sent >= limit:
        raise _error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "You are sending messages too quickly. Please wait a few seconds and try again.",
            headers={"Retry-After": "10"},
        )


# ---------- use cases ----------
def info(engine: ChatbotEngine) -> ChatInfo:
    return ChatInfo(
        mode="ai" if engine.ai_enabled else "guide",
        provider=engine.provider.name if engine.provider else None,
        max_message_chars=get_settings().chat_max_message_chars,
        starters=STARTERS,
        disclaimer=DISCLAIMER,
    )


def send_message(db: Session, user: User, engine: ChatbotEngine, raw_message: str, conversation_id: int | None) -> ChatReplyOut:
    settings = get_settings()
    student = profile_service.get_student(db, user)
    message = clean_message(raw_message)
    check_rate_limit(db, student.id)

    if conversation_id is not None:
        conversation = repo.get_owned(db, student.id, conversation_id)
        if conversation is None:
            raise _error(status.HTTP_404_NOT_FOUND, "Conversation not found.")
        if repo.message_count(db, conversation.id) >= settings.chat_max_messages_per_conversation:
            raise _error(status.HTTP_409_CONFLICT, "This conversation is full. Please start a new one.")
        previous = repo.recent_messages(db, conversation.id, settings.chat_history_turns * 2)
    else:
        now = _now()
        conversation = ChatConversation(student_id=student.id, title=make_title(message), created_at=now, updated_at=now)
        db.add(conversation)
        previous = []

    history = [ChatTurn(m.role.value, m.content) for m in previous]
    draft = engine.reply(db, user, student, message, history)

    user_msg = ChatMessage(conversation=conversation, role=ChatRole.USER, content=message)
    bot_msg = ChatMessage(conversation=conversation, role=ChatRole.ASSISTANT, content=draft.text, source=draft.source)
    conversation.updated_at = _now()
    db.add_all([user_msg, bot_msg])
    db.commit()
    return ChatReplyOut(
        conversation=to_conversation_out(conversation, repo.message_count(db, conversation.id)),
        user_message=to_message_out(user_msg),
        reply=to_message_out(bot_msg),
        suggestions=draft.suggestions[:4],
    )


def list_conversations(db: Session, user: User) -> list[ConversationOut]:
    student = profile_service.get_student(db, user)
    return [to_conversation_out(c, n) for c, n in repo.list_with_counts(db, student.id)]


def get_conversation(db: Session, user: User, conversation_id: int) -> ConversationDetail:
    student = profile_service.get_student(db, user)
    c = repo.get_owned(db, student.id, conversation_id)
    if c is None:
        raise _error(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    base = to_conversation_out(c, len(c.messages))
    return ConversationDetail(**base.model_dump(), messages=[to_message_out(m) for m in c.messages])


def delete_conversation(db: Session, user: User, conversation_id: int) -> None:
    student = profile_service.get_student(db, user)
    c = repo.get_owned(db, student.id, conversation_id)
    if c is None:
        raise _error(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    db.delete(c)
    db.commit()


def delete_all(db: Session, user: User) -> int:
    student = profile_service.get_student(db, user)
    removed = repo.delete_all(db, student.id)
    db.commit()
    return removed
