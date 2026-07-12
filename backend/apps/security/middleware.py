"""Request-path security middleware.

``EdgeGuardMiddleware`` (early — right after request timing) runs the
IP-level defence chain on every request::

    trusted-proxy IP resolution -> IP rules (trust/allow/deny) ->
    IP reputation -> bot detection -> WAF-lite -> burst limit (token bucket)
    -> sustained limit (sliding window)

``TenantRateLimitMiddleware`` (right after tenant resolution) adds the
workspace-scoped, plan-aware limit so one tenant can never starve another.

Both are configuration-driven and hot-reloadable; in ``monitor`` mode every
check still runs and logs but nothing is blocked. Denials return the
platform's standard JSON envelope. Per-user limits are enforced at the DRF
layer (``throttling.py``) where authentication has already happened.
"""
import logging

from django.http import JsonResponse

from . import engine, reputation
from .botdetect import classify
from .conf import get_config
from .events import record
from .ip import resolve_client_ip
from .waf import inspect

logger = logging.getLogger("apps.security")


def _deny(status: int, message: str, code: str, headers: dict | None = None) -> JsonResponse:
    # Mirrors StandardJSONRenderer / tenants middleware envelope.
    response = JsonResponse(
        {"success": False, "message": message, "data": None, "meta": {"code": code}},
        status=status,
    )
    for name, value in (headers or {}).items():
        response[name] = value
    return response


def _skip(request, config) -> bool:
    if request.method == "OPTIONS":  # CORS preflight — carries no credentials
        return True
    return config.is_exempt_path(request.path)


def _apply_headers(response, decision, window_seconds):
    for name, value in decision.headers(window_seconds).items():
        response.setdefault(name, value)


class EdgeGuardMiddleware:
    """Layer 1 (application edge): everything that can be decided from the
    connection + request line alone, before any DB/auth work happens."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        config = get_config()
        if not config.enabled:
            return self.get_response(request)
        if _skip(request, config):
            return self.get_response(request)

        # ---- client identity (spoof-resistant) --------------------------- #
        addr = resolve_client_ip(request, config)
        request.client_ip = addr.ip
        request.client_addr = addr
        if addr.suspicious_chain:
            record("proxy_suspect", "logged", request,
                   dedupe=f"proxy:{addr.ip}", chain=addr.proxy_chain)

        # ---- IP rules (operator verdicts always win) --------------------- #
        matched = config.match_ip_rule(addr.parsed, None)
        if matched:
            action, rule_id = matched
            if action == "trust":
                request.security_trusted = True
                return self.get_response(request)
            if action == "deny":
                # An explicit operator deny blocks even in monitor mode.
                record("ip_denied", "blocked", request, rule_id=rule_id)
                return _deny(403, "Access denied.", "request_blocked")
            request.security_allowlisted = True  # "allow": skip limits below

        allowlisted = getattr(request, "security_allowlisted", False)

        # ---- IP reputation ------------------------------------------------ #
        if not allowlisted:
            rep_status, score = reputation.status(addr.ip)
            request.threat_score = score
            if rep_status == reputation.STATUS_BLOCKED:
                if config.monitor_only:
                    record("reputation_block", "logged", request, threat_score=score)
                else:
                    record("reputation_block", "blocked", request, threat_score=score)
                    return _deny(403, "Access temporarily blocked.", "request_blocked",
                                 {"Retry-After": str(config.get("reputation.block_seconds", 3600))})

        # ---- bot detection ------------------------------------------------ #
        verdict = classify(request.META.get("HTTP_USER_AGENT", ""), config)
        if verdict.action == "block":
            reputation.penalize(addr.ip, "bot_blocked")
            if config.section_enforces("bots"):
                record("bot_detected", "blocked", request,
                       category=verdict.category, matched=verdict.matched)
                return _deny(403, "Automated traffic is not allowed.", "bot_blocked")
            record("bot_detected", "logged", request, dedupe=f"bot:{addr.ip}",
                   category=verdict.category, matched=verdict.matched)
        elif verdict.action == "log":
            record("bot_detected", "logged", request, dedupe=f"bot:{addr.ip}",
                   category=verdict.category, matched=verdict.matched)

        # ---- WAF (request-line hygiene) ----------------------------------- #
        violations = inspect(request, config)
        if violations:
            score = reputation.penalize(addr.ip, "waf_violation")
            detail = {"rules": [v.rule for v in violations],
                      "matched": violations[0].detail}
            if config.section_enforces("waf"):
                record("waf_violation", "blocked", request, threat_score=score, **detail)
                return _deny(403, "Request rejected.", "request_blocked")
            record("waf_violation", "logged", request, threat_score=score, **detail)

        # ---- IP rate limits ------------------------------------------------ #
        decision = None
        if not allowlisted:
            decision = engine.check("ip_burst", addr.ip)
            if decision.allowed:
                decision = engine.check("ip_global", addr.ip)
            if not decision.allowed:
                score = reputation.penalize(addr.ip, "rate_limited")
                if config.monitor_only:
                    record("rate_limited", "logged", request, dedupe=f"rl:{addr.ip}",
                           scope=decision.scope, threat_score=score)
                    decision = None  # don't stamp deny headers on an allowed response
                else:
                    record("rate_limited", "blocked", request, dedupe=f"rl:{addr.ip}",
                           scope=decision.scope, threat_score=score)
                    if decision.meta.get("reason") == "fail_closed":
                        return _deny(503, "Service protection engaged. Try again shortly.",
                                     "fail_closed", decision.headers())
                    return _deny(429, "Too many requests. Slow down.", "rate_limited",
                                 decision.headers(config.get(
                                     "rate_limits.ip_global.window_seconds", 60)))

        response = self.get_response(request)

        if decision is not None and decision.limit > 0 \
                and config.get("response.include_headers", True) \
                and request.path.startswith("/api/"):
            _apply_headers(response, decision,
                           config.get("rate_limits.ip_global.window_seconds", 60))
        return response


class TenantRateLimitMiddleware:
    """Layer 2 (workspace isolation): per-tenant, plan-aware global limit.
    Runs after TenantResolutionMiddleware so ``request.tenant`` is set."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        config = get_config()
        tenant = getattr(request, "tenant", None)
        if (
            not config.enabled
            or tenant is None
            or getattr(request, "security_trusted", False)
            or getattr(request, "security_allowlisted", False)
            or _skip(request, config)
        ):
            return self.get_response(request)

        # Tenant-scoped operator rules (a workspace can ban an address for
        # itself without platform-wide effect).
        addr = getattr(request, "client_addr", None)
        if addr is not None:
            matched = config.match_ip_rule(addr.parsed, tenant.pk)
            if matched and matched[0] == "deny":
                record("ip_denied", "blocked", request, rule_id=matched[1],
                       tenant_rule=True)
                return _deny(403, "Access denied.", "request_blocked")

        decision = engine.check(
            "tenant_global",
            str(tenant.pk),
            multiplier=config.plan_multiplier(self._plan_slug(tenant)),
        )
        if not decision.allowed and not config.monitor_only:
            record("rate_limited", "blocked", request, dedupe=f"rlt:{tenant.pk}",
                   scope="tenant_global")
            return _deny(429, "This workspace is sending too many requests.",
                         "tenant_rate_limited",
                         decision.headers(config.get(
                             "rate_limits.tenant_global.window_seconds", 60)))

        return self.get_response(request)

    @staticmethod
    def _plan_slug(tenant) -> str:
        # Use the plan FK only when already loaded (never an extra query on
        # the hot path); the legacy plan_name is a free fallback.
        plan = tenant._state.fields_cache.get("plan") if hasattr(tenant, "_state") else None
        if plan is not None:
            return getattr(plan, "slug", "") or ""
        return getattr(tenant, "plan_name", "") or ""
