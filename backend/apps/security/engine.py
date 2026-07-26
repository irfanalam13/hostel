"""Rate-limit engine: rule resolution + backend selection + fail strategy.

The single entry point every enforcement layer uses (middleware, DRF
throttles, and the endpoint-specific limits in the next document)::

    from apps.security.engine import check

    decision = check("ip_global", identity=client_ip)
    if not decision.allowed: ...429...

Behaviour:

* Backend "auto" (default): Redis when reachable, per-process memory while it
  isn't (circuit breaker in ``redis_client``) — every decision stays atomic
  and multi-container-correct on Redis; the memory window is the documented
  degraded mode.
* Fail strategy: a Redis error mid-evaluation applies ``fail_strategy`` —
  *open* allows the request (availability first), *closed* denies it.
* Multipliers scale a rule per caller (plan-based tenant limits) without
  duplicating rule definitions.
"""
import logging

from . import redis_client
from .algorithms import Decision, MemoryBackend, RedisBackend, evaluate
from .conf import get_config

logger = logging.getLogger("apps.security")

_KEY_PREFIX = "sec:rl:"

_memory_backend = MemoryBackend()
_redis_backend = None  # cached wrapper; rebuilt if the client reconnects


def _get_backend(config):
    """(backend, degraded) — degraded=True when auto/redis had to fall back."""
    global _redis_backend

    preference = str(config.get("backend", "auto")).lower()
    if preference == "memory":
        return _memory_backend, False

    client = redis_client.get_client()
    if client is None:
        if preference == "redis":
            return None, True          # hard requirement not met
        return _memory_backend, True   # auto -> degrade
    if _redis_backend is None or _redis_backend.client is not client:
        _redis_backend = RedisBackend(client)
    return _redis_backend, False


def _fail_decision(config, scope: str) -> Decision:
    if config.fail_open:
        return Decision(allowed=True, scope=scope, degraded=True)
    return Decision(allowed=False, scope=scope, degraded=True, retry_after=5,
                    meta={"reason": "fail_closed"})


def _scaled(rule: dict, multiplier: float) -> dict:
    if multiplier == 1.0:
        return rule
    scaled = dict(rule)
    for field in ("limit", "capacity", "burst"):
        if field in scaled:
            scaled[field] = max(1, int(round(scaled[field] * multiplier)))
    if "refill_rate" in scaled:
        scaled["refill_rate"] = max(0.001, float(scaled["refill_rate"]) * multiplier)
    return scaled


def check(scope: str, identity: str, rule: dict | None = None,
          cost: int = 1, multiplier: float = 1.0) -> Decision:
    """Evaluate one scope for one caller.

    ``scope``    — a key under ``rate_limits`` in the config (or any custom
                   name when ``rule`` is passed explicitly).
    ``identity`` — who is being limited (ip, tenant slug, user id, ...).
    ``rule``     — explicit rule dict; default: ``rate_limits.<scope>``.
    ``multiplier`` — scales the rule's limits (plan entitlements).
    """
    config = get_config()

    # Emergency kill switch: rate limiting fully bypassed (allow all) when an
    # operator has engaged it via the Super-Admin API. Hot-reloaded.
    if config.get("kill.rate_limiter"):
        return Decision(allowed=True, scope=scope)

    if rule is None:
        rule = config.get(f"rate_limits.{scope}") or {}
    if not rule or not rule.get("enabled", True):
        return Decision(allowed=True, scope=scope)

    backend, degraded = _get_backend(config)
    if backend is None:
        return _fail_decision(config, scope)

    key = f"{_KEY_PREFIX}{scope}:{identity}"
    try:
        decision = evaluate(backend, key, _scaled(rule, multiplier), cost)
    except Exception:
        logger.warning("rate-limit evaluation failed for %s", scope, exc_info=True)
        if backend is not _memory_backend:
            redis_client.mark_down()
            # One in-request retry on the memory fallback keeps some limiting
            # in place for the rest of this Redis outage window.
            try:
                decision = evaluate(_memory_backend, key, _scaled(rule, multiplier), cost)
                decision.degraded = True
            except Exception:
                return _fail_decision(config, scope)
        else:
            return _fail_decision(config, scope)

    decision.scope = scope
    decision.degraded = decision.degraded or degraded

    # Prometheus decision counter (no-op without prometheus_client).
    try:
        from . import metrics

        metrics.record_rate_limit(scope, decision.allowed, decision.degraded)
    except Exception:
        pass

    return decision


def reset_for_tests() -> None:
    global _memory_backend, _redis_backend
    _memory_backend = MemoryBackend()
    _redis_backend = None
