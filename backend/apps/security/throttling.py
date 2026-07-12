"""DRF throttle classes backed by the distributed engine.

These are the FOUNDATION classes the endpoint-specific limits (login, signup,
OTP, APIs, AI, …) will subclass in the next document. Unlike DRF's built-in
throttles (django-cache history lists, non-atomic read-modify-write) these are
atomic on Redis, tenant/plan-aware, respect monitor mode and the fail
strategy, and stamp standard X-RateLimit headers via the middleware pattern.

Usage (next document)::

    class LoginThrottle(SecurityScopedThrottle):
        scope = "auth_login"      # a rate_limits.auth_login config rule

The rule is pure configuration: hot-reloadable, per-environment, overridable
per plan/tenant via multipliers.
"""
from rest_framework.throttling import BaseThrottle

from . import engine
from .conf import get_config


class SecurityScopedThrottle(BaseThrottle):
    """Throttles by a named config rule (``rate_limits.<scope>``). Identity
    defaults to user id when authenticated, else the spoof-resistant client
    IP resolved by EdgeGuardMiddleware."""

    scope: str = ""

    def get_identity(self, request, view) -> str:
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False):
            return f"u:{user.pk}"
        return f"ip:{getattr(request, 'client_ip', self.get_ident(request))}"

    def get_multiplier(self, request, view) -> float:
        return 1.0

    def allow_request(self, request, view):
        config = get_config()
        if not config.enabled or not self.scope:
            return True
        if getattr(request, "security_trusted", False) or getattr(
            request, "security_allowlisted", False
        ):
            return True
        decision = engine.check(
            self.scope,
            self.get_identity(request, view),
            multiplier=self.get_multiplier(request, view),
        )
        self._decision = decision
        if decision.allowed or config.monitor_only:
            return True
        return False

    def wait(self):
        decision = getattr(self, "_decision", None)
        return decision.retry_after if decision else None


class TenantScopedThrottle(SecurityScopedThrottle):
    """Same, but the budget is shared by the whole workspace and scaled by
    its plan multiplier — for tenant-priced resources (exports, AI, bulk)."""

    def get_identity(self, request, view) -> str:
        tenant = getattr(request, "tenant", None)
        if tenant is not None:
            return f"t:{tenant.pk}"
        return super().get_identity(request, view)

    def get_multiplier(self, request, view) -> float:
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return 1.0
        plan = tenant._state.fields_cache.get("plan") if hasattr(tenant, "_state") else None
        slug = (getattr(plan, "slug", "") or getattr(tenant, "plan_name", "") or "")
        return get_config().plan_multiplier(slug)


class IPScopedThrottle(SecurityScopedThrottle):
    """Always keys by client IP, even for authenticated callers — for
    credential-sensitive endpoints where per-account limits aren't enough."""

    def get_identity(self, request, view) -> str:
        return f"ip:{getattr(request, 'client_ip', self.get_ident(request))}"
