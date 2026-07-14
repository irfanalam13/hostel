"""Provider selection — the single switch point for the whole service.

``ML_PROVIDER`` picks the backend; everything else is config. Non-Ollama
providers are declared here as explicit extension points so the wiring is
obvious when they're implemented.
"""
from ..config import settings
from .base import LLMProvider
from .ollama_provider import OllamaProvider


def get_provider() -> LLMProvider:
    provider = settings.PROVIDER
    if provider == "ollama":
        return OllamaProvider(model=settings.MODEL, temperature=settings.TEMPERATURE)

    # Extension points — implement an LLMProvider subclass and return it here.
    # The agent loop and SSE layer need no changes; they only see `Chunk`s.
    if provider in {"openai", "azure", "anthropic", "groq", "openrouter", "deepseek", "mistral"}:
        raise NotImplementedError(
            f"Provider '{provider}' is configured but not yet implemented. "
            "Add an LLMProvider subclass in app/llm and wire it into get_provider()."
        )

    raise ValueError(f"Unknown ML_PROVIDER: {provider!r}")
