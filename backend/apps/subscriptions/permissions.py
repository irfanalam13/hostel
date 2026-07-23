"""Access control for the platform (Super Admin) subscription surface.

Platform administration is intentionally NOT part of the tenant RBAC catalog:
tenant OWNER/ADMIN roles hold the ``*`` wildcard within their workspace, which
would otherwise sweep in any platform permission. Platform authority is a
distinct axis — Django ``is_superuser`` — enforced by this class. The frontend
mirrors it as the ``SUPER_ADMIN`` role / ``platform:manage`` permission.
"""
from rest_framework.permissions import BasePermission


class IsPlatformAdmin(BasePermission):
    """Only platform staff (``is_superuser``) may manage plans/features.

    Used by every write endpoint in the Super-Admin subscription API
    (Modules 2–8, 19). Read-only public plan listing has its own gates.
    """

    message = "Platform administrator access is required."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_superuser)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
