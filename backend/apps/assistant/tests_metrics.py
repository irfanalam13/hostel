"""Tests for AI cost estimation + metric emission (Phase 4, §4)."""
from decimal import Decimal

from .metrics import estimate_cost, record_ai_usage


def test_self_hosted_is_free():
    assert estimate_cost("ollama", "llama3.2:3b", 1000, 1000) == Decimal("0.0000")


def test_unknown_model_is_zero():
    assert estimate_cost("openai", "some-future-model", 1000, 1000) == Decimal("0.0000")


def test_gemini_flash_priced():
    # 1M prompt + 1M completion @ (0.075, 0.30) = 0.375 USD
    cost = estimate_cost("gemini", "gemini-flash-latest", 1_000_000, 1_000_000)
    assert cost == Decimal("0.3750")


def test_longest_substring_wins():
    # "gpt-4o-mini" must not be captured by the shorter "gpt-4o" entry.
    mini = estimate_cost("openai", "gpt-4o-mini", 1_000_000, 0)
    full = estimate_cost("openai", "gpt-4o", 1_000_000, 0)
    assert mini == Decimal("0.1500") and full == Decimal("2.5000")


def test_record_ai_usage_never_raises():
    # Must be safe whether prometheus_client is present or not.
    record_ai_usage(
        provider="gemini", model="gemini-flash-latest", kind="chat", success=True,
        tokens_prompt=100, tokens_completion=50, cost_usd=Decimal("0.0001"), latency_ms=850,
    )
