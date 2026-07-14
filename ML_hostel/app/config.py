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
    PORT = int(os.getenv("ML_PORT", "9000"))

    # Django gateway (service-internal URL). Tool callbacks + context + complete
    # all go here; it is the ONLY way this service touches business data.
    DJANGO_API_URL = os.getenv("ML_DJANGO_API_URL", "http://web:8000/api").rstrip("/")

    # Shared HMAC secret used to verify the context token minted by Django. MUST
    # match Django's ML_SHARED_SECRET exactly (no fallback here — fail closed).
    SHARED_SECRET = os.getenv("ML_SHARED_SECRET", "")

    # Browser origins allowed to open the SSE stream (CORS). In the single-origin
    # dev/prod gateway setup this can stay empty (same-origin via nginx).
    ALLOWED_ORIGINS = _csv(os.getenv("ML_ALLOWED_ORIGINS", ""))

    TOOL_TIMEOUT = float(os.getenv("ML_TOOL_TIMEOUT", "15"))

    # --- LLM provider ---------------------------------------------------------
    PROVIDER = os.getenv("ML_PROVIDER", "ollama").lower()
    MODEL = os.getenv("ML_MODEL", "llama3.2:3b")
    TEMPERATURE = float(os.getenv("ML_TEMPERATURE", "0.2"))
    MAX_TOOL_ROUNDS = int(os.getenv("ML_MAX_TOOL_ROUNDS", "4"))

    # Ollama
    OLLAMA_URL = os.getenv("ML_OLLAMA_URL", "http://ollama:11434").rstrip("/")

    # --- RAG / embeddings (Phase 2) ------------------------------------------
    EMBED_MODEL = os.getenv("ML_EMBED_MODEL", "nomic-embed-text")
    CHUNK_SIZE = int(os.getenv("ML_CHUNK_SIZE", "1200"))       # chars per chunk (approx)
    CHUNK_OVERLAP = int(os.getenv("ML_CHUNK_OVERLAP", "200"))  # char overlap between chunks
    RAG_TOP_K = int(os.getenv("ML_RAG_TOP_K", "5"))            # chunks retrieved per query

    # OpenAI / Azure / Anthropic (used only when PROVIDER selects them)
    OPENAI_API_KEY = os.getenv("ML_OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("ML_OPENAI_BASE_URL", "https://api.openai.com/v1")
    ANTHROPIC_API_KEY = os.getenv("ML_ANTHROPIC_API_KEY", "")

    @property
    def cors_enabled(self) -> bool:
        return bool(self.ALLOWED_ORIGINS)


settings = Settings()
