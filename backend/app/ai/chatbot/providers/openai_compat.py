"""OpenAI, or any server that speaks the OpenAI "chat completions" format (set LLM_BASE_URL)."""
import httpx

from app.ai.chatbot.providers.base import ChatTurn, LLMError, error_for_status, normalize_turns

DEFAULT_MODEL = "gpt-4o-mini"  # override with LLM_MODEL
DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAICompatibleProvider:
    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "",
        base_url: str = "",
        timeout: float = 20.0,
        max_tokens: int = 600,
        client: httpx.Client | None = None,
    ):
        self._api_key = api_key
        self.model = model or DEFAULT_MODEL
        self._url = (base_url or DEFAULT_BASE_URL).rstrip("/") + "/chat/completions"
        self._timeout = timeout
        self._max_tokens = max_tokens
        self._client = client

    def generate(self, system: str, turns: list[ChatTurn]) -> str:
        conversation = [{"role": t.role, "content": t.content} for t in normalize_turns(turns)]
        if not conversation:
            raise LLMError("bad_request", "no user message")
        body = {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "system", "content": system}, *conversation],
        }
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        try:
            client = self._client or httpx.Client(timeout=self._timeout)
            try:
                response = client.post(self._url, json=body, headers=headers, timeout=self._timeout)
            finally:
                if self._client is None:
                    client.close()
        except httpx.TimeoutException as exc:
            raise LLMError("timeout", type(exc).__name__) from exc
        except httpx.HTTPError as exc:
            raise LLMError("unavailable", type(exc).__name__) from exc

        if response.status_code != 200:
            error_type = ""
            try:
                error_type = str(response.json().get("error", {}).get("type", ""))
            except (ValueError, AttributeError):
                pass
            raise error_for_status(response.status_code, error_type)
        try:
            text = (response.json()["choices"][0]["message"]["content"] or "").strip()
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("bad_response", "unexpected response shape") from exc
        if not text:
            raise LLMError("bad_response", "empty reply")
        return text
