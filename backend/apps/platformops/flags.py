"""Feature-flag evaluation engine.

``is_enabled(key, hostel=, user=)`` is the single entry point used by backend
code; the frontend gets the fully-resolved set via the ops status endpoint.

Evaluation order (first decisive rule wins):
    1. flag missing            -> False
    2. flag.kill               -> False   (emergency per-flag kill switch)
    3. live override (user > hostel) -> override.enabled
    4. flag.is_active is False -> False
    5. role targeting mismatch -> False
    6. hostel allow/block list -> block wins
    7. percentage rollout      -> deterministic bucket by tenant|user|global

Flag definitions are cached (short TTL + signal invalidation) so evaluation is
a dict lookup, not a query, on the hot path.
"""
from __future__ import annotations

import hashlib

from django.core.cache import cache

_CACHE_KEY = "platformops:flags:v1"
_CACHE_TTL = 30  # seconds; also invalidated on save/delete via signals


def _load_flags() -> dict:
    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return cached

    from .models import FeatureFlag

    flags = {}
    for f in FeatureFlag.objects.all():
        flags[f.key] = {
            "is_active": f.is_active,
            "kill": f.kill,
            "rollout": int(f.rollout_percentage or 0),
            "allowed_hostels": {str(h) for h in (f.allowed_hostels or [])},
            "blocked_hostels": {str(h) for h in (f.blocked_hostels or [])},
            "allowed_roles": {str(r) for r in (f.allowed_roles or [])},
        }
    cache.set(_CACHE_KEY, flags, _CACHE_TTL)
    return flags


def invalidate_cache():
    cache.delete(_CACHE_KEY)


def _bucket(key: str, identifier: str) -> int:
    """Stable 0-99 bucket so a given (flag, identifier) is always in/out."""
    digest = hashlib.sha256(f"{key}:{identifier}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def _override_for(key, hostel_id, user):
    """Most-specific live (non-expired) override: user-level beats tenant-level."""
    from django.db.models import Q

    from .models import FeatureFlagOverride

    user_id = getattr(user, "pk", None)
    if not user_id and not hostel_id:
        return None

    target = Q()
    if user_id:
        target |= Q(user_id=user_id)
    if hostel_id:
        target |= Q(hostel_id=hostel_id)

    # is_live covers active + scheduling window ([starts_at, expires_at)).
    candidates = [
        ov for ov in FeatureFlagOverride.objects.filter(flag__key=key).filter(target)
        if ov.is_live
    ]
    # user-level takes precedence over tenant-level
    for ov in candidates:
        if ov.user_id and ov.user_id == user_id:
            return ov
    for ov in candidates:
        if ov.hostel_id and str(ov.hostel_id) == str(hostel_id):
            return ov
    return None


def is_enabled(key: str, *, hostel=None, user=None) -> bool:
    flags = _load_flags()
    flag = flags.get(key)
    if flag is None:
        return False
    if flag["kill"]:
        return False

    hostel_id = getattr(hostel, "id", None) or (hostel if isinstance(hostel, str) else None)

    override = _override_for(key, hostel_id, user)
    if override is not None:
        return override.enabled

    if not flag["is_active"]:
        return False

    if flag["allowed_roles"]:
        role = getattr(user, "role", None)
        if getattr(user, "is_superuser", False):
            return True
        if role is None or str(role) not in flag["allowed_roles"]:
            return False

    if hostel_id is not None:
        hid = str(hostel_id)
        if flag["blocked_hostels"] and hid in flag["blocked_hostels"]:
            return False
        if flag["allowed_hostels"]:
            return hid in flag["allowed_hostels"]

    rollout = flag["rollout"]
    if rollout >= 100:
        return True
    if rollout <= 0:
        return False
    identifier = str(hostel_id or getattr(user, "pk", None) or "global")
    return _bucket(key, identifier) < rollout


def evaluate_all(*, hostel=None, user=None) -> dict:
    """Resolve every flag for a given context (used by the status endpoint)."""
    return {key: is_enabled(key, hostel=hostel, user=user) for key in _load_flags()}
