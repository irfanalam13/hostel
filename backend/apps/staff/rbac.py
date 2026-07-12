"""Custom-role permission resolution for staff members.

Bridges the per-tenant :class:`apps.staff.models.Role` into the core RBAC
engine: ``apps.common.rbac.user_permissions`` calls
:func:`extra_permissions_for_user` and unions the result into a user's
effective permission set (purely additive).

The expanded grant set for each role is cached per role id (invalidated by
``apps.staff.signals`` on any role change); the profile → role lookup is light
and further memoized per request by the core engine.
"""
from django.core.cache import cache

from apps.common.rbac import expand_grants

_ROLE_PERMS_KEY = "staffrole:v1:{role_id}"
_ROLE_PERMS_TTL = 300


def role_grant_set(role) -> frozenset:
    """Expanded ``module.action`` permissions for a custom Role, Redis-cached."""
    if role is None or not getattr(role, "is_active", False):
        return frozenset()
    key = _ROLE_PERMS_KEY.format(role_id=role.pk)
    try:
        hit = cache.get(key)
    except Exception:
        hit = None
    if hit is not None:
        return frozenset(hit)
    perms = expand_grants(role.permissions or [])
    try:
        cache.set(key, list(perms), _ROLE_PERMS_TTL)
    except Exception:
        pass
    return perms


def invalidate_role_cache(role_id) -> None:
    try:
        cache.delete(_ROLE_PERMS_KEY.format(role_id=role_id))
    except Exception:
        pass  # TTL bounds staleness


def extra_permissions_for_user(user, hostel) -> frozenset:
    """Permissions contributed by the user's assigned custom staff role in this
    workspace (empty when the user has no active staff profile/role here)."""
    if hostel is None or not user or not getattr(user, "is_authenticated", False):
        return frozenset()
    from .models import StaffProfile

    profile = (
        StaffProfile.objects.filter(user=user, hostel=hostel, is_deleted=False)
        .select_related("role")
        .first()
    )
    if profile is None or profile.role_id is None:
        return frozenset()
    return role_grant_set(profile.role)
