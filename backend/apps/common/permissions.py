from django.conf import settings
from rest_framework.permissions import BasePermission

# Roles with staff-level (write) access on legacy role-gated endpoints.
# READ_ONLY / STUDENT / PARENT / RESIDENT are deliberately absent — they get
# read access where a view allows it and everything finer goes through the
# permission registry in apps.common.rbac.
STAFF_ROLES = {"ADMIN", "OWNER", "MANAGER", "RECEPTIONIST", "ACCOUNTANT", "WARDEN", "STAFF"}

# Membership is checked on every authenticated request (authentication AND
# permission layer), so it is cached: per-request memo first, then Redis with a
# short TTL. UserHostel save/delete invalidates the Redis entry (wired in
# apps.accounts.apps), so revocation takes effect immediately on the ORM path
# and within the TTL worst-case otherwise.
_MEMBERSHIP_KEY = "membership:v1:{user_id}:{hostel_id}"


def _membership_ttl() -> int:
    return int(getattr(settings, "MEMBERSHIP_CACHE_TTL", 60))


def membership_cache_key(user_id, hostel_id) -> str:
    return _MEMBERSHIP_KEY.format(user_id=user_id, hostel_id=hostel_id)


def invalidate_membership_cache(user_id, hostel_id) -> None:
    from django.core.cache import cache

    try:
        cache.delete(membership_cache_key(user_id, hostel_id))
    except Exception:
        pass  # cache down — TTL bounds staleness


def user_is_hostel_member(user, hostel, request=None):
    """True if the authenticated user is actively linked to the hostel.

    Superusers bypass the check. This is the core multi-tenant guard: the
    resolved hostel comes from a client-supplied header, so we must verify the
    caller actually belongs to it before exposing any data.

    Pass ``request`` when available: the result is memoized on the request so
    the authentication class and permission classes share one lookup.
    """
    if hostel is None:
        return False
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    # Per-request memo (authentication + permissions both call this).
    base = getattr(request, "_request", request) if request is not None else None
    memo_key = (user.pk, hostel.pk)
    if base is not None:
        memo = getattr(base, "_membership_memo", None)
        if memo is not None and memo_key in memo:
            return memo[memo_key]

    from django.core.cache import cache

    cache_key = membership_cache_key(user.pk, hostel.pk)
    result = None
    try:
        hit = cache.get(cache_key)
    except Exception:  # cache down — serve from the DB, don't 500 the request
        hit = None
    if hit is not None:
        result = bool(hit)

    if result is None:
        # Imported lazily to avoid a circular import (accounts -> common.models).
        from apps.accounts.models import UserHostel

        result = UserHostel.objects.filter(user=user, hostel=hostel, is_active=True).exists()
        try:
            cache.set(cache_key, 1 if result else 0, _membership_ttl())
        except Exception:
            pass

    if base is not None:
        if getattr(base, "_membership_memo", None) is None:
            base._membership_memo = {}
        base._membership_memo[memo_key] = result
    return result


class HasHostelContext(BasePermission):
    """Requires a resolved hostel. For authenticated callers, also requires
    that the caller is a member of that hostel (prevents cross-tenant access
    via a spoofed X-Hostel-Code header). Anonymous callers are allowed through
    only so explicitly-public endpoints (e.g. public admission form) keep
    working — those views must still create records scoped to request.hostel."""

    message = "Missing/invalid hostel context or you are not a member of this hostel."

    def has_permission(self, request, view):
        hostel = getattr(request, "hostel", None)
        if hostel is None:
            return False
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            return user_is_hostel_member(user, hostel, request=request)
        return True


class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "role", None) in {"ADMIN", "OWNER"}


class IsOwnerOrManager(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "role", None) in {"ADMIN", "OWNER", "MANAGER"}


class IsSuperUser(BasePermission):
    """Platform staff only. Super admins (``is_superuser``) run the SaaS itself;
    tenant owners/managers must never see cross-cutting platform/infrastructure
    surfaces (system health, PWA telemetry, plan management). Mirrors the
    frontend ``platform:manage`` gate so hiding the UI and refusing the API
    stay in lockstep."""

    message = "This is a platform-operator surface (super admin only)."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_superuser)


class IsAccountant(BasePermission):
    """Financial roles: owners/admins/managers plus accountants."""
    def has_permission(self, request, view):
        return getattr(request.user, "role", None) in {"ADMIN", "OWNER", "MANAGER", "ACCOUNTANT"}


class IsStaffOrReadOnly(BasePermission):
    """Authenticated hostel members may read; only staff roles may write.

    The authentication check is essential: this class is almost always paired
    with ``HasHostelContext``, which lets *anonymous* callers through (so the
    public admission form keeps working). Without requiring auth here, any
    anonymous caller who knows a hostel code could read that tenant's data via
    GET. Membership of the resolved hostel is still enforced by
    ``HasHostelContext`` for authenticated users.
    """

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return getattr(user, "role", None) in STAFF_ROLES


class HostelMemberCanCreateStaffCanEdit(BasePermission):
    """
    Allows any authenticated hostel user to view/create self-service records,
    while limiting updates and destructive changes to staff roles.
    """
    staff_roles = STAFF_ROLES

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS", "POST"):
            return True
        return getattr(request.user, "role", None) in self.staff_roles


class IsStaff(BasePermission):
    """
    Allows access only to authenticated staff users.
    Assumes request.user.is_staff or role check exists.
    """
    def has_permission(self, request, view):
        role = getattr(request.user, "role", None)
        return bool(
            request.user
            and request.user.is_authenticated
            and (getattr(request.user, "is_staff", False) or role in STAFF_ROLES)
        )


class IsHostelResolved(BasePermission):
    """
    Ensure the request has an active hostel context AND that the authenticated
    user is a member of it (multi-tenant SaaS isolation). The hostel itself is
    set by apps.tenants.middleware.TenantResolutionMiddleware (workspace
    subdomain, X-WORKSPACE, or legacy X-Hostel-Code header).
    """
    message = "Hostel is not selected/resolved, or you are not a member of it."

    def has_permission(self, request, view):
        hostel = getattr(request, "hostel", None)
        if hostel is None:
            return False
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            return user_is_hostel_member(user, hostel, request=request)
        return False
