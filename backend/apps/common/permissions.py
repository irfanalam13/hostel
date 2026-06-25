from rest_framework.permissions import BasePermission

STAFF_ROLES = {"ADMIN", "OWNER", "MANAGER", "ACCOUNTANT", "WARDEN", "STAFF"}


def user_is_hostel_member(user, hostel):
    """True if the authenticated user is actively linked to the hostel.

    Superusers bypass the check. This is the core multi-tenant guard: the
    resolved hostel comes from a client-supplied header, so we must verify the
    caller actually belongs to it before exposing any data.
    """
    if hostel is None:
        return False
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    # Imported lazily to avoid a circular import (accounts -> common.models).
    from apps.accounts.models import UserHostel

    return UserHostel.objects.filter(user=user, hostel=hostel, is_active=True).exists()


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
            return user_is_hostel_member(user, hostel)
        return True


class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "role", None) in {"ADMIN", "OWNER"}


class IsOwnerOrManager(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "role", None) in {"ADMIN", "OWNER", "MANAGER"}


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
    set by HostelResolveMiddleware from the X-Hostel-Code header.
    """
    message = "Hostel is not selected/resolved, or you are not a member of it."

    def has_permission(self, request, view):
        hostel = getattr(request, "hostel", None)
        if hostel is None:
            return False
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            return user_is_hostel_member(user, hostel)
        return False
