from functools import lru_cache

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.ai.chatbot.providers import build_provider
from app.core.config import get_settings
from app.core.deps import require_student
from app.database.session import get_db
from app.models import User
from app.schemas.chat import ChatInfo, ChatReplyOut, ChatRequest, ConversationDetail, ConversationOut
from app.services import chat_service
from app.services.chatbot_engine import ChatbotEngine

router = APIRouter(prefix="/chat", tags=["Chatbot"])


@lru_cache
def _default_engine() -> ChatbotEngine:
    settings = get_settings()
    return ChatbotEngine(build_provider(settings), share_profile=settings.llm_share_profile)


def get_engine() -> ChatbotEngine:
    """Dependency: the configured chatbot (tests replace it with one that uses a fake provider)."""
    return _default_engine()


@router.get("/info", response_model=ChatInfo)
def chat_info(_: User = Depends(require_student), engine: ChatbotEngine = Depends(get_engine)):
    """Whether an AI model or the built-in guide is answering, plus starter questions."""
    return chat_service.info(engine)


@router.post("/messages", response_model=ChatReplyOut)
def send_message(
    data: ChatRequest,
    user: User = Depends(require_student),
    engine: ChatbotEngine = Depends(get_engine),
    db: Session = Depends(get_db),
):
    """Send a message and get the assistant's reply. Without `conversation_id` a new conversation starts."""
    return chat_service.send_message(db, user, engine, data.message, data.conversation_id)


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(user: User = Depends(require_student), db: Session = Depends(get_db)):
    """The logged-in student's conversations, most recent first."""
    return chat_service.list_conversations(db, user)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    return chat_service.get_conversation(db, user, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    chat_service.delete_conversation(db, user, conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/conversations", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_conversations(user: User = Depends(require_student), db: Session = Depends(get_db)):
    """Delete the student's entire chat history."""
    chat_service.delete_all(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
