"""Chooses how each message is answered. This is the chatbot's brain; it knows nothing about HTTP.

    1. Hiring decisions / schedules  -> an honest "I cannot know that" (no model involved)
    2. The student's own PlaceGenie data -> exact answers from the database (no model involved)
    3. Greetings / help               -> short fixed replies
    4. Everything else (general placement questions):
         - an LLM, if one is configured, given reference notes from the guide and a contact-free summary
         - otherwise, or if the LLM fails, the built-in placement guide
"""
import logging

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.chatbot import intents, knowledge
from app.ai.chatbot.intents import JobRef
from app.ai.chatbot.prompt import build_system_prompt
from app.ai.chatbot.providers import ChatTurn, LLMError, LLMProvider
from app.ai.chatbot.types import SOURCE_AI, SOURCE_FALLBACK, SOURCE_GUIDE, SOURCE_HELP, Draft
from app.models import JobStatus, Student, User
from app.repositories import job_repository
from app.services import chat_data

logger = logging.getLogger("placegenie.chatbot")

STARTERS = [
    "Which jobs am I eligible for?",
    "Recommend jobs for me",
    "Show my upcoming interviews",
    "How can I improve my resume?",
    "How should I prepare for a technical interview?",
    "What is my skill gap?",
]

GREETING = (
    "Hi! I'm the PlaceGenie assistant. I can check your eligibility, suggest jobs, show your applications and "
    "interviews, review your resume, and give placement and interview advice. What would you like to do?"
)
THANKS = "You're welcome! Ask me anything else about your placements."
OUT_OF_SCOPE = (
    "I focus on placement preparation and your PlaceGenie information, so I may not be able to help with that. "
    "I can help with things like interview and aptitude preparation, resume tips, job roles and skills, "
    "or checking your eligibility for a job."
)
FALLBACK_NOTICE = "The AI assistant is not available right now, so this answer comes from the built-in placement guide."
LOOKUP_FAILED = "Sorry, I could not look that up just now. You can find it in PlaceGenie on the Jobs, Applications or Interviews pages."
MAX_REPLY_CHARS = 3000


def _trim(text: str) -> str:
    text = text.replace("\r\n", "\n").strip()
    if len(text) <= MAX_REPLY_CHARS:
        return text
    cut = text[:MAX_REPLY_CHARS]
    end = max(cut.rfind(". "), cut.rfind("\n"))
    return (cut[: end + 1] if end > MAX_REPLY_CHARS // 2 else cut).rstrip() + " ..."


class ChatbotEngine:
    def __init__(self, provider: LLMProvider | None, *, share_profile: bool = True):
        self.provider = provider
        self.share_profile = share_profile

    @property
    def ai_enabled(self) -> bool:
        return self.provider is not None

    # ------------------------------------------------------------------
    def reply(self, db: Session, user: User, student: Student, message: str, history: list[ChatTurn]) -> Draft:
        jobs = self._open_jobs(db)
        intent = intents.detect_intent(message, jobs)

        if intent == intents.GENERAL:
            return self._general(db, user, student, message, history)
        return self._by_intent(db, user, intent, message, jobs)

    # ------------------------------------------------------------------
    def _open_jobs(self, db: Session) -> list[JobRef]:
        rows, _ = job_repository.search_jobs(db, job_repository.JobFilters(status=JobStatus.OPEN), 1000, 0)
        return [JobRef(j.id, j.title, j.company.name) for j in rows]

    def _by_intent(self, db: Session, user: User, intent: str, message: str, jobs: list[JobRef]) -> Draft:
        if intent == intents.GREETING:
            return Draft(GREETING, SOURCE_HELP, STARTERS[:3])
        if intent == intents.THANKS:
            return Draft(THANKS, SOURCE_HELP, STARTERS[:2])
        if intent == intents.HELP:
            about = knowledge.TOPICS_BY_ID["about"]
            return Draft(about.answer, SOURCE_HELP, STARTERS[:4])
        if intent == intents.REALTIME:
            return chat_data.realtime_limit()

        handlers = {
            intents.ELIGIBILITY: lambda: chat_data.eligibility(db, user, message, jobs),
            intents.SKILL_GAP: lambda: chat_data.skill_gap(db, user, message, jobs),
            intents.RECOMMEND: lambda: chat_data.recommend(db, user),
            intents.APPLICATIONS: lambda: chat_data.applications(db, user, message),
            intents.INTERVIEWS: lambda: chat_data.interviews(db, user),
            intents.RESUME: lambda: chat_data.resume(db, user),
            intents.PROFILE: lambda: chat_data.profile(db, user),
        }
        try:
            return handlers[intent]()
        except SQLAlchemyError:
            raise  # a database problem is reported as such by the API, not hidden in the chat
        except HTTPException as exc:  # e.g. the job was closed a moment ago
            logger.info("Data handler %s refused: %s", intent, exc.detail)
            return Draft(LOOKUP_FAILED, SOURCE_FALLBACK, STARTERS[:2])
        except Exception:  # noqa: BLE001 - never let one handler bug break the conversation
            logger.exception("Data handler %s failed", intent)
            return Draft(LOOKUP_FAILED, SOURCE_FALLBACK, STARTERS[:2])

    # ------------------------------------------------------------------
    def _general(self, db: Session, user: User, student: Student, message: str, history: list[ChatTurn]) -> Draft:
        if self.provider is None:
            return self._guide(message)
        try:
            return self._ask_llm(db, user, student, message, history)
        except LLMError as exc:
            logger.warning("LLM call failed (%s): %s", exc.kind, exc.detail)  # never log the API key or message text
            return self._degraded(message)
        except SQLAlchemyError:
            raise  # database problems are reported by the API, not disguised as an AI outage
        except Exception:  # noqa: BLE001 - a misbehaving provider must never break the chat
            logger.exception("Unexpected error from the LLM provider")
            return self._degraded(message)

    def _degraded(self, message: str) -> Draft:
        guide = self._guide(message)
        return Draft(f"{FALLBACK_NOTICE}\n\n{guide.text}", SOURCE_FALLBACK, guide.suggestions)

    def _guide(self, message: str) -> Draft:
        found = knowledge.best_answer(message)
        if found is None:
            return Draft(OUT_OF_SCOPE, SOURCE_HELP, STARTERS[:4])
        text, follow_ups = found
        return Draft(text, SOURCE_GUIDE, list(follow_ups))

    def _ask_llm(self, db: Session, user: User, student: Student, message: str, history: list[ChatTurn]) -> Draft:
        notes = [(m.topic.title, m.topic.answer) for m in knowledge.search(message, 3)]
        summary = chat_data.build_summary(db, student, user) if self.share_profile else None
        system = build_system_prompt(summary, notes)
        text = self.provider.generate(system, [*history, ChatTurn("user", message)])
        text = _trim(text)
        if not text:
            raise LLMError("bad_response", "empty after trimming")
        follow_ups = knowledge.best_answer(message)
        return Draft(text, SOURCE_AI, list(follow_ups[1]) if follow_ups else STARTERS[:3])
