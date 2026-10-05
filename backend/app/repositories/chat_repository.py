from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import ChatConversation, ChatMessage, ChatRole


def get_owned(db: Session, student_id: int, conversation_id: int) -> ChatConversation | None:
    """A conversation only if it belongs to this student; anyone else's looks 'not found'."""
    return db.scalar(
        select(ChatConversation)
        .where(ChatConversation.id == conversation_id, ChatConversation.student_id == student_id)
        .options(selectinload(ChatConversation.messages))
    )


def list_with_counts(db: Session, student_id: int) -> list[tuple[ChatConversation, int]]:
    """Most recently active first. 'Active' = newest message id, which unlike a timestamp cannot tie."""
    stats = (
        select(
            ChatMessage.conversation_id,
            func.count(ChatMessage.id).label("n"),
            func.max(ChatMessage.id).label("last_id"),
        )
        .group_by(ChatMessage.conversation_id)
        .subquery()
    )
    rows = db.execute(
        select(ChatConversation, func.coalesce(stats.c.n, 0))
        .outerjoin(stats, stats.c.conversation_id == ChatConversation.id)
        .where(ChatConversation.student_id == student_id)
        .order_by(func.coalesce(stats.c.last_id, 0).desc(), ChatConversation.id.desc())
    ).all()
    return [(c, int(n)) for c, n in rows]


def message_count(db: Session, conversation_id: int) -> int:
    return db.scalar(select(func.count(ChatMessage.id)).where(ChatMessage.conversation_id == conversation_id)) or 0


def recent_messages(db: Session, conversation_id: int, limit: int) -> list[ChatMessage]:
    rows = db.scalars(
        select(ChatMessage).where(ChatMessage.conversation_id == conversation_id).order_by(ChatMessage.id.desc()).limit(limit)
    ).all()
    return list(reversed(rows))


def user_messages_since(db: Session, student_id: int, since: datetime) -> int:
    return (
        db.scalar(
            select(func.count(ChatMessage.id))
            .join(ChatConversation, ChatConversation.id == ChatMessage.conversation_id)
            .where(ChatConversation.student_id == student_id, ChatMessage.role == ChatRole.USER, ChatMessage.created_at >= since)
        )
        or 0
    )


def delete_all(db: Session, student_id: int) -> int:
    ids = list(db.scalars(select(ChatConversation.id).where(ChatConversation.student_id == student_id)))
    if ids:
        db.execute(delete(ChatMessage).where(ChatMessage.conversation_id.in_(ids)))
        db.execute(delete(ChatConversation).where(ChatConversation.id.in_(ids)))
    return len(ids)
