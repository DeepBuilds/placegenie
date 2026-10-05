"""Claude through the Anthropic Messages API (plain HTTPS via httpx, no extra SDK)."""
import httpx

from app.ai.chatbot.providers.base import ChatTurn, LLMError, error_for_status, normalize_turns

DEFAULT_MODEL = "claude-haiku-4-5-20251001"  # small and fast; override with LLM_MODEL
DEFAULT_BASE_URL = "https://api.anthropic.com"
API_VERSION = "2023-06-01"


class AnthropicProvider:
    name = "anthropic"

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
        self._url = (base_url or DEFAULT_BASE_URL).rstrip("/") + "/v1/messages"
        self._timeout = timeout
        self._max_tokens = max_tokens
        self._client = client

    def generate(self, system: str, turns: list[ChatTurn]) -> str:
        messages = [{"role": t.role, "content": t.content} for t in normalize_turns(turns)]
        if not messages:
            raise LLMError("bad_request", "no user message")
        body = {"model": self.model, "max_tokens": self._max_tokens, "system": system, "messages": messages}
        headers = {"x-api-key": self._api_key, "anthropic-version": API_VERSION, "content-type": "application/json"}
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
            except ValueError:
                pass
            raise error_for_status(response.status_code, error_type)
        try:
            blocks = response.json()["content"]
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise LLMError("bad_response", "unexpected response shape") from exc
        if not text:
            raise LLMError("bad_response", "empty reply")
        return text
