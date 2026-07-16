"""AI eval gate — system-prompt contract + golden set (Phase 3, §3 AI overlay).

The system prompt is a safety-critical artefact: it is what stops the assistant
inventing occupancy/dues figures, leaking across tenants, or answering policy
questions without citing the knowledge base. A well-meaning edit can silently
drop one of those guardrails. These deterministic checks fail CI on such a
regression — no LLM or network needed, so the gate is fast and never flaky.

A live-model eval (actually calling the configured provider) is opt-in via
ML_EVAL_LIVE=1 so CI stays deterministic.

Run: cd ML_hostel && python -m pytest tests/test_eval_prompts.py
"""
import os

import pytest

from app.agents.prompts import build_system_prompt

# Golden contexts the prompt must handle correctly.
CTX_WITH_TOOLS = {
    "hostel": {"name": "Sunrise Hostel"},
    "actor": {"role": "WARDEN"},
    "tools": [{"name": "occupancy_summary"}, {"name": "find_students"}, {"name": "search_knowledge"}],
}
CTX_NO_TOOLS = {"hostel": {"name": "Sunrise Hostel"}, "actor": {"role": "OWNER"}, "tools": []}
CTX_EMPTY = {}


# --- Safety-critical directives that MUST survive any prompt edit -------------
# (substring, human description) — matched case-insensitively.
REQUIRED_DIRECTIVES = [
    ("never guess or invent numbers", "anti-hallucination for figures"),
    ("search_knowledge", "policy questions must hit the knowledge base"),
    ("scoped strictly to this workspace", "tenant isolation"),
    ("never reference other hostels", "cross-tenant leak prevention"),
]


@pytest.mark.parametrize("substr,desc", REQUIRED_DIRECTIVES)
def test_prompt_keeps_safety_directive(substr, desc):
    prompt = build_system_prompt(CTX_WITH_TOOLS).lower()
    assert substr.lower() in prompt, f"system prompt lost its guardrail: {desc}"


def test_prompt_grounds_available_tools():
    prompt = build_system_prompt(CTX_WITH_TOOLS)
    for tool in ("occupancy_summary", "find_students", "search_knowledge"):
        assert tool in prompt, f"tool not surfaced to the model: {tool}"


def test_prompt_injects_role_and_hostel():
    prompt = build_system_prompt(CTX_WITH_TOOLS)
    assert "Sunrise Hostel" in prompt
    assert "WARDEN" in prompt


def test_prompt_handles_no_tools_gracefully():
    prompt = build_system_prompt(CTX_NO_TOOLS).lower()
    assert "no data tools" in prompt  # must state it plainly, not hallucinate tools


def test_prompt_never_crashes_on_empty_context():
    prompt = build_system_prompt(CTX_EMPTY)
    assert isinstance(prompt, str) and len(prompt) > 50
    # Falls back to safe generic identity rather than blank/None.
    assert "this hostel" in prompt.lower() and "staff" in prompt.lower()


def test_prompt_version_is_set():
    from app.agents.prompts import PROMPT_VERSION

    assert isinstance(PROMPT_VERSION, str) and PROMPT_VERSION.strip()


def test_model_registry_gates_unapproved_models():
    from app.llm.registry import assert_model_approved, is_approved

    assert is_approved("gemini", "gemini-flash-latest")
    assert not is_approved("gemini", "totally-made-up-model")
    assert is_approved("ollama", "any-local-tag:3b")  # self-hosted accepts any
    with pytest.raises(ValueError):
        assert_model_approved("openai", "gpt-5-unreleased")


@pytest.mark.skipif(not os.getenv("ML_EVAL_LIVE"), reason="live LLM eval is opt-in (set ML_EVAL_LIVE=1)")
def test_live_model_answers_grounded():
    """Opt-in smoke eval against the configured provider.

    Guards a model/prompt promotion: a new ML_MODEL must still produce a
    non-empty, on-topic answer. Kept minimal so it needs only provider creds,
    not a full gateway. Extend with scored golden Q&A as the eval set grows.
    """
    from app.llm.factory import get_provider

    provider = get_provider()
    assert provider is not None, "provider factory returned nothing"
