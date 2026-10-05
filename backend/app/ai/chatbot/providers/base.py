"""The provider abstraction: anything that can turn a system prompt + conversation into a reply.

Adding another LLM (Gemini, a local model, ...) means writing one class with `name` and `generate`
and registering it in `factory.py`. Nothing else in the chatbot knows which provider is in use.
"""
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class ChatTurn:
    role: Literal["user", "assistant"]
    content: str


class LLMError(Exception):
    """A failed call to the LLM service.

    `kind` is a short category the application can act on; `detail` is for server logs only and is
    never shown to students (it must not contain secrets).
    """

    def __init__(self, kind: str, detail: str = ""):
        super().__init__(f"{kind}: {detail}" if detail else kind)
        self.kind = kind  # auth | rate_limit | timeout | unavailable | bad_request | bad_response
        self.detail = detail


class LLMProvider(Protocol):
    name: str

    def generate(self, system: str, turns: list[ChatTurn]) -> str:
        """Return the assistant's reply text, or raise LLMError."""
        ...


def normalize_turns(turns: list[ChatTurn]) -> list[ChatTurn]:
    """Most chat APIs need the conversation to start with the user and alternate roles.

    Consecutive messages from the same side are merged; leading assistant messages are dropped.
    """
    merged: list[ChatTurn] = []
    for turn in turns:
        if not turn.content.strip():
            continue
        if merged and merged[-1].role == turn.role:
            merged[-1] = ChatTurn(turn.role, merged[-1].content + "\n\n" + turn.content)
        elif merged or turn.role == "user":
            merged.append(turn)
    return merged


def error_for_status(status: int, error_type: str = "") -> LLMError:
    if status in (401, 403):
        return LLMError("auth", f"HTTP {status} {error_type}".strip())
    if status == 429:
        return LLMError("rate_limit", "HTTP 429")
    if status >= 500:
        return LLMError("unavailable", f"HTTP {status}")
    return LLMError("bad_request", f"HTTP {status} {error_type}".strip())
