"""Provider selection — the single switch point for the whole service.

``ML_PROVIDER`` picks the backend; everything else is config. Ollama is the
self-hosted default; Gemini/OpenAI/Groq/OpenRouter all share one OpenAI-compatible
adapter (base URL + key differ, resolved in ``settings.openai_compat``).
"""
from ..config import settings
from .base import LLMProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAICompatProvider

_OPENAI_COMPAT = {"openai", "azure", "gemini", "groq", "openrouter", "deepseek", "mistral", "together"}


def get_provider() -> LLMProvider:
    provider = settings.PROVIDER

    if provider == "ollama":
        return OllamaProvider(model=settings.MODEL, temperature=settings.TEMPERATURE)

    if provider in _OPENAI_COMPAT:
        conf = settings.openai_compat
        if not conf["api_key"]:
            raise ValueError(f"Provider '{provider}' selected but no API key configured.")
        return OpenAICompatProvider(
            model=settings.MODEL,
            base_url=conf["base_url"],
            api_key=conf["api_key"],
            temperature=settings.TEMPERATURE,
            name=provider,
        )

    raise ValueError(f"Unknown ML_PROVIDER: {provider!r}")
