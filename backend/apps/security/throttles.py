"""Concrete DRF throttle classes for Prompt 08.

Built on the foundation base classes (`throttling.py`) so every one is
atomic on Redis, tenant/plan-aware, monitor-mode-aware and fail-strategy-aware
— unlike DRF's built-in cache-history throttles. Each maps to a `rate_limits.*`
config scope, so limits are pure configuration (hot-reloadable, per-env,
per-plan).

Two families:

* **Auth throttles** — keyed by client IP (anonymous endpoints), one per
  sensitive auth surface. Attached to the auth views alongside the existing
  progressive-lockout/CAPTCHA logic (defence in depth: the throttle is the
  blunt per-IP ceiling, progressive lockout is the per-identity escalation).
* **Resource throttles** — `RoleRateThrottle` (global per-role/plan/method
  budget for every authenticated request) plus tenant-scoped throttles for
  expensive surfaces (exports, analytics, search, AI, notifications, payments,
  uploads).
"""
import logging

from rest_framework.throttling import (
    AnonRateThrottle,
    ScopedRateThrottle,
    UserRateThrottle,
)

from .throttling import IPScopedThrottle, SecurityScopedThrottle, TenantScopedThrottle
from . import engine
from .conf import get_config

logger = logging.getLogger("apps.security")


# --------------------------------------------------------------------------- #
# Cache-resilient wrappers for DRF's built-in throttles
# --------------------------------------------------------------------------- #
# DRF's built-in throttles (Anon/User/Scoped) keep their history in the Django
# cache and call ``cache.get``/``cache.set`` directly, with no error handling.
# When the cache backend (Redis) is unreachable, that call raises and turns
# EVERY anonymous endpoint that reaches the throttle stage — most visibly
# ``/api/auth/csrf/``, which the SPA hits before it can do anything — into a
# 500. The platform's own engine-backed throttles already degrade to an
# in-process window on a Redis outage (see ``engine.check``); these wrappers
# give the built-ins the same contract so a cache outage never 500s, matching
# the promise in the ``CACHES`` note in settings.
try:  # redis-py errors don't subclass builtin ConnectionError, so name them.
    from redis.exceptions import RedisError as _RedisError

    _CACHE_ERRORS = (_RedisError, ConnectionError, TimeoutError, OSError)
except Exception:  # pragma: no cover - redis always present in this stack
    _CACHE_ERRORS = (ConnectionError, TimeoutError, OSError)


class CacheResilientThrottleMixin:
    """Fail open (allow the request) when the throttle's cache is unreachable.

    Availability first: the edge/tenant rate limiters and ``RoleRateThrottle``
    still apply, so failing this redundant layer open during a cache outage is
    the right trade-off — and it stops a Redis outage from 500-ing the auth
    handshake.
    """

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except _CACHE_ERRORS:
            logger.warning(
                "throttle cache unavailable; failing open for %s",
                getattr(self, "scope", type(self).__name__),
                exc_info=True,
            )
            return True


class ResilientAnonRateThrottle(CacheResilientThrottleMixin, AnonRateThrottle):
    pass


class ResilientUserRateThrottle(CacheResilientThrottleMixin, UserRateThrottle):
    pass


class ResilientScopedRateThrottle(CacheResilientThrottleMixin, ScopedRateThrottle):
    pass


# --------------------------------------------------------------------------- #
# Authentication endpoint throttles (per client IP)
# --------------------------------------------------------------------------- #
class LoginRateThrottle(IPScopedThrottle):
    scope = "auth_login"


class SignupRateThrottle(IPScopedThrottle):
    scope = "auth_signup"


class SignupOTPRateThrottle(IPScopedThrottle):
    scope = "auth_signup_otp"


class OTPVerifyRateThrottle(IPScopedThrottle):
    scope = "auth_otp_verify"


class PasswordResetRateThrottle(IPScopedThrottle):
    scope = "auth_password_reset"


class PasswordChangeRateThrottle(SecurityScopedThrottle):
    # Authenticated: key by user so one account's change attempts are bounded.
    scope = "auth_password_change"


class TokenRefreshRateThrottle(IPScopedThrottle):
    scope = "auth_token_refresh"


class MFAVerifyRateThrottle(IPScopedThrottle):
    scope = "auth_mfa_verify"


class ForgotHostelRateThrottle(IPScopedThrottle):
    scope = "auth_forgot_hostel"


class SessionRevokeRateThrottle(SecurityScopedThrottle):
    scope = "auth_session_revoke"


# --------------------------------------------------------------------------- #
# Expensive / abuse-prone resource throttles (per workspace, plan-scaled)
# --------------------------------------------------------------------------- #
class ExportRateThrottle(TenantScopedThrottle):
    scope = "exports"


class ReportRateThrottle(TenantScopedThrottle):
    scope = "reports"


class AnalyticsRateThrottle(TenantScopedThrottle):
    scope = "analytics"


class SearchRateThrottle(TenantScopedThrottle):
    scope = "search"


class NotificationSendRateThrottle(TenantScopedThrottle):
    scope = "notifications_send"


class AIRateThrottle(TenantScopedThrottle):
    scope = "ai"


class PaymentRateThrottle(TenantScopedThrottle):
    scope = "payment"


class FileUploadRateThrottle(TenantScopedThrottle):
    scope = "file_upload"


# --------------------------------------------------------------------------- #
# Global per-role / per-plan / per-method API budget
# --------------------------------------------------------------------------- #
class RoleRateThrottle(SecurityScopedThrottle):
    """A single global budget for every request, resolved from the caller's
    role (config `role_limits.roles`), scaled by the workspace plan multiplier,
    with writes costing more than reads (`role_limits.method_costs`).

    Anonymous callers use `role_limits.anon`. This is the "per user / per role
    / per plan / per method" API policy the whole platform inherits without
    touching individual views; endpoint-specific throttles compose on top.
    """

    scope = "role_limits"

    def allow_request(self, request, view):
        config = get_config()
        role_conf = config.get("role_limits") or {}
        if not config.enabled or not role_conf.get("enabled", True):
            return True
        if getattr(request, "security_trusted", False) or getattr(
            request, "security_allowlisted", False
        ):
            return True

        user = getattr(request, "user", None)
        authed = getattr(user, "is_authenticated", False)
        window = int(role_conf.get("window_seconds", 60))
        method = (request.method or "GET").upper()
        cost = int((role_conf.get("method_costs") or {}).get(method, 1))
        if cost <= 0:  # e.g. OPTIONS — never counted
            return True

        if authed:
            role = "SUPER_ADMIN" if getattr(user, "is_superuser", False) else (
                getattr(user, "role", "") or "default")
            roles = role_conf.get("roles") or {}
            limit = int(roles.get(role, roles.get("default", 240)))
            identity = f"u:{user.pk}"
            multiplier = self.get_multiplier(request, view)
        else:
            limit = int(role_conf.get("anon", 60))
            identity = f"ip:{getattr(request, 'client_ip', self.get_ident(request))}"
            multiplier = 1.0

        rule = {
            "enabled": True,
            "algorithm": role_conf.get("algorithm", "sliding_window"),
            "limit": limit,
            "window_seconds": window,
        }
        decision = engine.check(
            self.scope, identity, rule=rule, cost=cost, multiplier=multiplier
        )
        self._decision = decision
        return decision.allowed or config.monitor_only

    def get_multiplier(self, request, view):
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return 1.0
        plan = tenant._state.fields_cache.get("plan") if hasattr(tenant, "_state") else None
        slug = (getattr(plan, "slug", "") or getattr(tenant, "plan_name", "") or "")
        return get_config().plan_multiplier(slug)
