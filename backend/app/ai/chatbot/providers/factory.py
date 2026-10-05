"""Chooses the provider from configuration. Anything misconfigured means "no provider" (never a crash)."""
import logging

import httpx

from app.ai.chatbot.providers.anthropic import AnthropicProvider
from app.ai.chatbot.providers.base import LLMProvider
from app.ai.chatbot.providers.openai_compat import OpenAICompatibleProvider
from app.core.config import Settings

logger = logging.getLogger("placegenie.chatbot")

# provider name (LLM_PROVIDER) -> class. Register new providers here.
PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAICompatibleProvider,
}


def build_provider(settings: Settings, client: httpx.Client | None = None) -> LLMProvider | None:
    name = (settings.llm_provider or "none").strip().lower()
    if name in ("", "none"):
        return None
    cls = PROVIDERS.get(name)
    if cls is None:
        logger.warning("Unknown LLM_PROVIDER %r (known: %s). The built-in guide will be used.", name, ", ".join(PROVIDERS))
        return None
    if not settings.llm_api_key.strip():
        logger.warning("LLM_PROVIDER=%s but LLM_API_KEY is empty. The built-in guide will be used.", name)
        return None
    return cls(
        api_key=settings.llm_api_key.strip(),
        model=settings.llm_model.strip(),
        base_url=settings.llm_base_url.strip(),
        timeout=settings.llm_timeout_seconds,
        max_tokens=settings.llm_max_tokens,
        client=client,
    )
