"""Prometheus metrics + cost estimation for the AI assistant (Phase 4, §4).

Turns the per-request ``AiUsage`` write-back into first-class Prometheus series
on the existing ``/metrics`` endpoint (django-prometheus), so the AI layer gets
the same observability as the rest of the backend: request/error rate, token
throughput, latency, and *cost* by provider/model.

Mirrors ``apps.security.metrics``: ``prometheus_client`` is imported guardedly,
so with it absent every function is a no-op and nothing breaks. Label
cardinality is bounded (provider/model/kind/success — all small fixed sets);
never per-user/per-tenant (that drill-down lives in the AI dashboard / Loki).
"""
from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal

logger = logging.getLogger("apps.assistant")

try:  # pragma: no cover - exercised via enabled/disabled branches
    from prometheus_client import Counter, Histogram

    _AVAILABLE = True
except Exception:  # prometheus_client absent -> metrics become no-ops
    _AVAILABLE = False


if _AVAILABLE:
    AI_REQUESTS = Counter(
        "hostel_ai_requests_total",
        "AI assistant completions by provider/model/kind and success.",
        ["provider", "model", "kind", "success"],
    )
    AI_TOKENS = Counter(
        "hostel_ai_tokens_total",
        "AI tokens consumed by provider/model and direction (prompt/completion).",
        ["provider", "model", "direction"],
    )
    AI_COST = Counter(
        "hostel_ai_cost_usd_total",
        "Estimated AI spend in USD by provider/model.",
        ["provider", "model"],
    )
    AI_LATENCY = Histogram(
        "hostel_ai_latency_seconds",
        "End-to-end AI completion latency by provider/model.",
        ["provider", "model"],
        buckets=(0.5, 1, 2, 4, 8, 15, 30, 60),
    )


# --- Cost table -------------------------------------------------------------
# USD per 1,000,000 tokens (input, output). Self-hosted (ollama) is free.
# Approximate list prices; update as providers change pricing. Matched by the
# first key that is a substring of the model name (longest first), so
# "gemini-flash-latest" resolves to the gemini-flash entry.
_PRICING_PER_M = {
    # model-substring : (input_per_million, output_per_million)
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gemini-flash": (0.075, 0.30),
    "gemini-pro": (1.25, 5.00),
    "llama-3.3-70b": (0.59, 0.79),  # e.g. Groq-hosted
}


def estimate_cost(provider: str, model: str, tokens_prompt: int, tokens_completion: int) -> Decimal:
    """Estimate request cost in USD (Decimal, 4dp). 0 for self-hosted/unknown."""
    if (provider or "").lower() == "ollama":
        return Decimal("0.0000")
    name = (model or "").lower()
    match = None
    for key in sorted(_PRICING_PER_M, key=len, reverse=True):
        if key in name:
            match = _PRICING_PER_M[key]
            break
    if match is None:
        return Decimal("0.0000")
    in_rate, out_rate = match
    cost = (Decimal(tokens_prompt) * Decimal(str(in_rate))
            + Decimal(tokens_completion) * Decimal(str(out_rate))) / Decimal(1_000_000)
    return cost.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def record_ai_usage(*, provider, model, kind, success, tokens_prompt,
                    tokens_completion, cost_usd, latency_ms) -> None:
    """Emit the AI metrics for one completion. No-op if prometheus is absent."""
    if not _AVAILABLE:
        return
    try:
        prov = provider or "unknown"
        mdl = model or "unknown"
        AI_REQUESTS.labels(prov, mdl, kind or "chat", "true" if success else "false").inc()
        if tokens_prompt:
            AI_TOKENS.labels(prov, mdl, "prompt").inc(tokens_prompt)
        if tokens_completion:
            AI_TOKENS.labels(prov, mdl, "completion").inc(tokens_completion)
        if cost_usd:
            AI_COST.labels(prov, mdl).inc(float(cost_usd))
        if latency_ms:
            AI_LATENCY.labels(prov, mdl).observe(latency_ms / 1000.0)
    except Exception:  # metrics must never break the request path
        logger.debug("ai metric emit failed", exc_info=True)
