"""Prometheus metrics for the security layer.

Exposes the rate-limiter / auth / threat activity as first-class Prometheus
series on the existing ``/metrics`` endpoint (django-prometheus, already wired
when ``PROMETHEUS_ENABLED=True``). Scraped by the observability stack
(deploy/observability) and visualised in the Security + Rate-Limit dashboards.

Design:

* ``prometheus_client`` is imported **guardedly** — if it (or django-prometheus)
  isn't installed, every function here is a no-op, so nothing breaks and the
  security layer keeps working without metrics.
* Metrics are emitted from ONE choke point (``events.record`` calls ``emit``),
  plus explicit rate-limit decision counting from the engine — so adding a new
  event type gets a metric for free with no extra wiring.
* Label cardinality is bounded on purpose: we label by event type / action /
  scope / result (all small, fixed sets), never by IP / user / path (unbounded)
  — high-cardinality drill-down belongs in Loki, not Prometheus.
"""
import logging

logger = logging.getLogger("apps.security")

try:  # pragma: no cover - exercised via the enabled/disabled branches
    from prometheus_client import Counter, Gauge

    _AVAILABLE = True
except Exception:  # prometheus_client absent -> metrics become no-ops
    _AVAILABLE = False


if _AVAILABLE:
    SECURITY_EVENTS = Counter(
        "hostel_security_events_total",
        "Security events emitted, by type and action (blocked/logged/allowed).",
        ["event_type", "action"],
    )
    RATE_LIMIT_DECISIONS = Counter(
        "hostel_rate_limit_decisions_total",
        "Rate-limit decisions by scope and result (allowed/limited/degraded).",
        ["scope", "result"],
    )
    AUTH_EVENTS = Counter(
        "hostel_auth_events_total",
        "Authentication protection events by type (failure/lockout/captcha).",
        ["event_type"],
    )
    WAF_BLOCKS = Counter(
        "hostel_waf_violations_total",
        "WAF rule matches by rule group.",
        ["rule"],
    )
    REPUTATION_BLOCKS = Gauge(
        "hostel_reputation_blocked_ips",
        "Approximate count of currently reputation-blocked IPs (best-effort).",
    )

_AUTH_EVENT_TYPES = {
    "auth_failure", "auth_lockout", "captcha_required", "captcha_failed",
    "api_role_limited", "replay_blocked",
}


def emit(event_type: str, action: str, detail: dict | None = None) -> None:
    """Record one security event as Prometheus series. Called from
    ``events.record`` so every event is counted. Never raises."""
    if not _AVAILABLE:
        return
    try:
        SECURITY_EVENTS.labels(event_type=event_type, action=action).inc()
        if event_type in _AUTH_EVENT_TYPES:
            AUTH_EVENTS.labels(event_type=event_type).inc()
        if event_type == "waf_violation" and detail:
            for rule in (detail.get("rules") or [])[:8]:
                WAF_BLOCKS.labels(rule=str(rule)).inc()
    except Exception:  # pragma: no cover - metrics must never break a request
        logger.debug("security metric emit failed", exc_info=True)


def record_rate_limit(scope: str, allowed: bool, degraded: bool = False) -> None:
    """Count a rate-limit decision. Called from the engine hot path."""
    if not _AVAILABLE:
        return
    try:
        result = "degraded" if degraded else ("allowed" if allowed else "limited")
        RATE_LIMIT_DECISIONS.labels(scope=scope or "-", result=result).inc()
    except Exception:  # pragma: no cover
        pass


def set_reputation_blocked(count: int) -> None:
    if not _AVAILABLE:
        return
    try:
        REPUTATION_BLOCKS.set(max(0, int(count)))
    except Exception:  # pragma: no cover
        pass


def available() -> bool:
    return _AVAILABLE
