"""High-level authentication-protection orchestration.

The single API the auth views/serializers call. It composes the primitives
(progressive lockout, CAPTCHA, abuse detection, reputation, events) so views
stay thin and every auth flow gets identical, config-driven protection:

    gate = check_gate("login", request, identity)      # BEFORE verifying creds
    if gate.blocked:      -> 429 with gate.retry_after
    if gate.captcha_required and not solved(request):   -> 403 captcha_required

    ...verify credentials...

    on failure:  register_failure("login", request, identity)
    on success:  register_success("login", request, identity)

Everything is enforcement-aware: in global monitor mode (or when the auth
layer is disabled) the checks still run and log but ``blocked`` is never
returned, so nothing breaks during a soak. Backward compatible: if a view
doesn't call these, behaviour is unchanged.
"""
import logging

from . import abuse, captcha, progressive
from .conf import get_config
from .events import record

logger = logging.getLogger("apps.security")


class GateDecision:
    __slots__ = ("blocked", "retry_after", "captcha_required", "reason", "failure_count")

    def __init__(self, blocked=False, retry_after=0, captcha_required=False,
                 reason="", failure_count=0):
        self.blocked = blocked
        self.retry_after = retry_after
        self.captcha_required = captcha_required
        self.reason = reason
        self.failure_count = failure_count


def _enabled() -> bool:
    config = get_config()
    if config.get("kill.auth"):
        return False  # emergency kill switch: auth protection bypassed
    return config.enabled and bool(config.get("auth.enabled", True))


def _enforcing() -> bool:
    # Auth blocking respects the global monitor switch (never block in monitor).
    return not get_config().monitor_only


def client_ip(request) -> str:
    """The spoof-resistant IP EdgeGuardMiddleware resolved; fall back to a
    direct resolve if this runs without the middleware (e.g. a unit test)."""
    ip = getattr(request, "client_ip", None)
    if ip:
        return ip
    try:
        from .ip import resolve_client_ip

        return resolve_client_ip(request, get_config()).ip
    except Exception:
        return request.META.get("REMOTE_ADDR", "") or ""


def make_identity(request, identifier: str) -> str:
    """Identity bucket for per-account tracking: the login identifier scoped
    to the resolved workspace, so the same username in two workspaces is
    tracked separately."""
    tenant = getattr(request, "tenant", None) or getattr(request, "hostel", None)
    tenant_part = str(getattr(tenant, "pk", "") or "-")
    return f"{tenant_part}:{(identifier or '').strip().lower()}"


def check_gate(scope: str, request, identity: str = "") -> GateDecision:
    """Pre-authentication gate. Call before verifying credentials."""
    if not _enabled():
        return GateDecision()

    ip = client_ip(request)
    state = progressive.is_locked(scope, ip, identity)
    if state.locked and _enforcing():
        record("auth_lockout", "blocked", request, dedupe=f"lock:{scope}:{ip}",
               scope=scope, retry_after=state.retry_after)
        return GateDecision(blocked=True, retry_after=state.retry_after,
                            reason="locked")

    count = progressive.failure_count(scope, ip, identity)
    if captcha.is_required(ip, count):
        return GateDecision(captcha_required=True, failure_count=count,
                            reason="captcha")
    return GateDecision(failure_count=count)


def verify_captcha_if_required(request, gate: GateDecision) -> bool:
    """True when either no CAPTCHA is required, or the submitted solution
    verifies. Reads the provider token from the request body/headers."""
    if not gate.captcha_required:
        return True
    token = ""
    field = captcha.response_field()
    data = getattr(request, "data", None) or {}
    token = data.get(field) or data.get("captcha_token") or ""
    if not token:
        token = request.headers.get("X-Captcha-Token", "")
    ok = captcha.verify(token, client_ip(request))
    if not ok:
        record("captcha_failed", "blocked", request, provider=captcha.provider())
    return ok


def register_failure(scope: str, request, identity: str = "",
                     credential_stuffing: bool = False) -> GateDecision:
    """Record a failed auth attempt. Returns the resulting state so the view
    can surface retry_after / captcha_required in its (generic) error."""
    if not _enabled():
        return GateDecision()

    ip = client_ip(request)
    abuse.record_brute_force(ip, request)
    if credential_stuffing and identity:
        abuse.record_credential_stuffing(ip, identity, request)

    state = progressive.register_failure(scope, ip, identity)
    record("auth_failure", "logged", request, dedupe=f"authfail:{scope}:{ip}",
           dedupe_ttl=30, scope=scope, failure_count=state.failure_count)

    blocked = state.locked and _enforcing()
    if state.locked:
        record("auth_lockout", "blocked" if blocked else "logged", request,
               scope=scope, retry_after=state.retry_after, tier=state.tier)
    return GateDecision(
        blocked=blocked, retry_after=state.retry_after if blocked else 0,
        captcha_required=captcha.is_required(ip, state.failure_count),
        failure_count=state.failure_count,
    )


def register_success(scope: str, request, identity: str = "") -> None:
    """Clear counters after a successful authentication."""
    if not _enabled():
        return
    progressive.reset(scope, client_ip(request), identity)


def note_enumeration(request, target: str) -> None:
    """Signal an enumeration-prone lookup (reset/forgot/signup-otp) so the
    scanning pattern is detected even though the response stays uniform."""
    if not _enabled():
        return
    abuse.record_enumeration(client_ip(request), target, request)
