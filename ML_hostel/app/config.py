"""Runtime configuration, all env-driven (mirrors the Django django-environ style).

Nothing here is provider-specific beyond defaults — switching the LLM backend is
a matter of setting ``ML_PROVIDER`` and the matching credentials, never a code
change (see ``app.llm.factory``).
"""
import os


def _csv(value: str) -> list[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


class Settings:
    # --- Identity / networking ------------------------------------------------
    SERVICE_NAME = "ml_hostel"
    HOST = os.getenv("ML_HOST", "0.0.0.0")
    PORT = int(os.getenv("ML_PORT", os.getenv("PORT", "9000")))  # Render injects $PORT

    # Django gateway (service-internal URL). Tool callbacks + context + complete
    # all go here; it is the ONLY way this service touches business data.
    DJANGO_API_URL = os.getenv("ML_DJANGO_API_URL", "http://web:8000/api").rstrip("/")

    # Shared HMAC secret used to verify the context token minted by Django. MUST
    # match Django's ML_SHARED_SECRET exactly (no fallback here — fail closed).
    SHARED_SECRET = os.getenv("ML_SHARED_SECRET", "")

    # Browser origins allowed to open the SSE stream (CORS). Required in prod
    # (the browser hits this service cross-origin — there is no nginx gateway).
    ALLOWED_ORIGINS = _csv(os.getenv("ML_ALLOWED_ORIGINS", ""))

    TOOL_TIMEOUT = float(os.getenv("ML_TOOL_TIMEOUT", "15"))

    # --- LLM provider (provider-agnostic; switch via ML_PROVIDER) ------------
    PROVIDER = os.getenv("ML_PROVIDER", "ollama").lower()
    TEMPERATURE = float(os.getenv("ML_TEMPERATURE", "0.2"))
    MAX_TOOL_ROUNDS = int(os.getenv("ML_MAX_TOOL_ROUNDS", "4"))

    # Ollama (self-hosted; default for local dev)
    OLLAMA_URL = os.getenv("ML_OLLAMA_URL", "http://ollama:11434").rstrip("/")

    # OpenAI-compatible hosted backends (OpenAI, Google Gemini, Groq, OpenRouter…)
    OPENAI_API_KEY = os.getenv("ML_OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("ML_OPENAI_BASE_URL", "https://api.openai.com/v1")
    GROQ_API_KEY = os.getenv("ML_GROQ_API_KEY", "")
    # Gemini via its OpenAI-compatibility layer.
    GEMINI_API_KEY = os.getenv("ML_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    GEMINI_BASE_URL = os.getenv(
        "ML_GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    _MODEL_ENV = os.getenv("ML_MODEL", "")
    _EMBED_ENV = os.getenv("ML_EMBED_MODEL", "")
    _DEFAULT_CHAT = {
        "ollama": "llama3.2:3b",
        "gemini": "gemini-flash-latest",
        "openai": "gpt-4o-mini",
        "groq": "llama-3.3-70b-versatile",
        "openrouter": "openai/gpt-4o-mini",
    }
    _DEFAULT_EMBED = {
        "ollama": "nomic-embed-text",
        "gemini": "gemini-embedding-001",
        "openai": "text-embedding-3-small",
    }

    # --- RAG / embeddings (Phase 2) ------------------------------------------
    CHUNK_SIZE = int(os.getenv("ML_CHUNK_SIZE", "1200"))       # chars per chunk (approx)
    CHUNK_OVERLAP = int(os.getenv("ML_CHUNK_OVERLAP", "200"))  # char overlap between chunks
    RAG_TOP_K = int(os.getenv("ML_RAG_TOP_K", "5"))            # chunks retrieved per query

    @property
    def MODEL(self) -> str:
        return self._MODEL_ENV or self._DEFAULT_CHAT.get(self.PROVIDER, "llama3.2:3b")

    @property
    def EMBED_MODEL(self) -> str:
        return self._EMBED_ENV or self._DEFAULT_EMBED.get(self.PROVIDER, "nomic-embed-text")

    @property
    def openai_compat(self) -> dict:
        """base_url + api_key for the OpenAI-compatible client, per provider."""
        if self.PROVIDER == "gemini":
            return {"base_url": self.GEMINI_BASE_URL.rstrip("/"), "api_key": self.GEMINI_API_KEY}
        if self.PROVIDER == "groq":
            return {"base_url": "https://api.groq.com/openai/v1", "api_key": self.GROQ_API_KEY}
        if self.PROVIDER == "openrouter":
            return {"base_url": "https://openrouter.ai/api/v1", "api_key": self.OPENAI_API_KEY}
        return {"base_url": self.OPENAI_BASE_URL.rstrip("/"), "api_key": self.OPENAI_API_KEY}

    @property
    def cors_enabled(self) -> bool:
        return bool(self.ALLOWED_ORIGINS)


settings = Settings()
