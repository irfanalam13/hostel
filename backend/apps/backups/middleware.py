"""Maintenance / emergency mode enforcement.

When the system DR mode is not ``normal``, this middleware gates requests:

  * maintenance — read-only: safe methods (GET/HEAD/OPTIONS) pass; writes are
    rejected with 503.
  * emergency   — full lock: everything is rejected with 503 except the exempt
    paths (health checks, auth, and the admin DR API, which is itself
    admin-only).

Enforcement is path+method based on purpose: JWT cookie auth runs in the DRF
layer (after this middleware), so ``request.user`` is not yet reliable here.
Admin recovery actions therefore go through the always-exempt DR API, whose own
permissions require an admin.
"""

import logging

from django.http import JsonResponse

logger = logging.getLogger("apps.backups")

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# Paths that must keep working even under full lock.
EXEMPT_PREFIXES = (
    "/health/",
    "/api/admin/",   # DR admin API — self-protected (admin-only)
    "/api/auth/",    # so an admin can still log in to drive recovery
    "/admin/",       # Django admin (superuser, session-authed)
    "/static/",
    "/media/",
)


def _is_exempt(path: str) -> bool:
    return any(path.startswith(p) for p in EXEMPT_PREFIXES)


def _blocked(mode: str, reason: str):
    resp = JsonResponse(
        {
            "detail": (
                "System is in maintenance mode (read-only)."
                if mode == "maintenance"
                else "System is locked for emergency disaster recovery."
            ),
            "mode": mode,
            "reason": reason,
        },
        status=503,
    )
    resp["Retry-After"] = "120"
    return resp


class DRModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Avoid a DB hit on the hot path for liveness and exempt routes.
        if request.method == "OPTIONS" or _is_exempt(request.path):
            return self.get_response(request)

        # Import lazily so the app imports cleanly before migrations run.
        # get_cached_state() serves from Redis; the DB is only hit on a cache
        # miss, so the normal-mode hot path costs one cache GET, not a query.
        try:
            from .models import DRMode, DRState

            mode, reason = DRState.get_cached_state()
        except Exception:  # noqa: BLE001 — never let the gate break the site
            return self.get_response(request)

        if mode == DRMode.NORMAL:
            return self.get_response(request)

        if mode == DRMode.MAINTENANCE:
            if request.method in SAFE_METHODS:
                return self.get_response(request)
            return _blocked(mode, reason)

        # EMERGENCY: full lock (exempt paths already returned above).
        return _blocked(mode, reason)
