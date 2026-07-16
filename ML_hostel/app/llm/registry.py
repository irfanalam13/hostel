"""Approved-model registry (Phase 6 AI/MLOps — model versioning guardrail).

Only vetted model IDs may run in production. A new model must be added here via
PR (which runs the eval gate) before it can be promoted — so an unreviewed model
can't silently reach users just by changing an env var. ``assert_model_approved``
is called at startup; the promotion flow (behind a feature flag + eval) is in
docs/AI_MLOPS.md.
"""
from __future__ import annotations

# provider -> set of approved model IDs. Keep in lockstep with config defaults.
APPROVED_MODELS: dict[str, set[str]] = {
    "gemini": {"gemini-flash-latest", "gemini-pro-latest", "gemini-1.5-flash"},
    "openai": {"gpt-4o-mini", "gpt-4o"},
    "groq": {"llama-3.3-70b-versatile"},
    "openrouter": {"openai/gpt-4o-mini"},
    # Self-hosted: any local tag is allowed (you control the box).
    "ollama": set(),  # empty = accept any (see is_approved)
}


def is_approved(provider: str, model: str) -> bool:
    provider = (provider or "").lower()
    if provider == "ollama":
        return True  # self-hosted, operator-controlled
    allowed = APPROVED_MODELS.get(provider)
    if allowed is None:
        return False  # unknown provider is not approved
    return model in allowed


def assert_model_approved(provider: str, model: str) -> None:
    """Raise if the configured model isn't vetted (fail-closed on promotion)."""
    if not is_approved(provider, model):
        raise ValueError(
            f"Model {model!r} for provider {provider!r} is not in the approved "
            f"registry (ML_hostel/app/llm/registry.py). Add it via PR + eval "
            f"before promoting. See docs/AI_MLOPS.md."
        )
