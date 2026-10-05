import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


def _now() -> datetime:
    """Naive local time, set from Python so it is consistent across MySQL and SQLite."""
    return datetime.now().replace(microsecond=0)


class ChatRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatConversation(TimestampMixin, Base):
    """One chat thread of one student. Messages belong to a conversation; the owner is derived from it."""

    __tablename__ = "chat_conversations"
    __table_args__ = (Index("ix_chat_conversations_student_updated", "student_id", "updated_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False, default="New chat")

    student = relationship("Student", back_populates="conversations")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    """Only what is needed to show the conversation again: who said it, what, how it was produced, when."""

    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_conversation_created", "conversation_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[ChatRole] = mapped_column(Enum(ChatRole, native_enum=False, length=20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # How an assistant reply was produced: data | guide | ai | fallback | limit | help (NULL for user messages)
    source: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, server_default=func.now(), nullable=False)

    conversation: Mapped[ChatConversation] = relationship(back_populates="messages")
