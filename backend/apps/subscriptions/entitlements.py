"""Runtime entitlement resolution (Module 10).

Given a hostel, resolve *what it can do*: which features are enabled and what
each limit is. The answer merges, in order of precedence:

    per-hostel override  >  the plan's PlanFeature/PlanLimit row  >  the
    catalog default (Feature.default_enabled / LimitDefinition.default_value)

Resolution is Redis-cached per hostel as a plain-dict snapshot (features +
limits), keyed by a global *generation* counter so any plan/catalog/override
change invalidates every hostel at once (see ``signals.py``). Usage counts are
never cached — they are read live at enforcement time (``usage.py``).

Everything degrades gracefully: a cache outage falls through to the DB, and a
hostel with no resolvable plan falls back to catalog defaults (a sane free
baseline) rather than erroring.
"""
import logging

from django.core.cache import cache

from .models import (
    Feature,
    FeatureOverride,
    LimitDefinition,
    LimitOverride,
    PlanFeature,
    PlanLimit,
    ReleaseStage,
)

logger = logging.getLogger(__name__)

_KEY = "entl:v1:{gen}:{hostel_id}"
_GEN_KEY = "entl:gen"
# Non-stable features never turn on via a plain catalog default — a hostel must
# be explicitly enrolled (a PlanFeature row or a FeatureOverride). This is the
# early-access gate (Module 14).
_DEFAULT_ELIGIBLE_STAGES = {ReleaseStage.STABLE}


def _ttl() -> int:
    from django.conf import settings

    return int(getattr(settings, "ENTITLEMENTS_CACHE_TTL", 300))


def _enforced() -> bool:
    """Whether plan-based gating is active. Off by default while the platform
    is still being built out (see ``settings.ENTITLEMENTS_ENFORCED``); when off,
    every feature reads as available and every limit as unlimited."""
    from django.conf import settings

    return bool(getattr(settings, "ENTITLEMENTS_ENFORCED", False))


def generation() -> int:
    try:
        gen = cache.get(_GEN_KEY)
        if gen is None:
            cache.add(_GEN_KEY, 1)
            gen = cache.get(_GEN_KEY) or 1
        return int(gen)
    except Exception:
        return 1


def bump_generation() -> None:
    """Invalidate every cached entitlement snapshot (called from signals)."""
    try:
        try:
            cache.incr(_GEN_KEY)
        except ValueError:
            # Key missing/expired — seed it; the old snapshots' gen no longer
            # matches, so they're already logically invalid.
            cache.set(_GEN_KEY, 1)
    except Exception:
        logger.warning("entitlement generation bump failed", exc_info=True)


def invalidate_hostel(hostel) -> None:
    """Drop one hostel's cached snapshot (e.g. its plan pointer changed)."""
    if hostel is None:
        return
    try:
        cache.delete(_KEY.format(gen=generation(), hostel_id=str(hostel.pk)))
    except Exception:
        logger.warning("entitlement hostel invalidation failed", exc_info=True)


# --------------------------------------------------------------------------- #
# Plan resolution
# --------------------------------------------------------------------------- #
def resolve_plan(hostel):
    """The Plan currently governing a hostel, or ``None``.

    Canonical pointer (``Hostel.plan``) first, then the newest active
    Subscription, then a match on the legacy free-text ``plan_name``.
    """
    if hostel is None:
        return None
    if getattr(hostel, "plan_id", None):
        return hostel.plan

    from apps.tenants.models import Plan

    sub = (
        hostel.subscriptions.filter(status="active")
        .select_related("plan")
        .order_by("-start_date")
        .first()
    )
    if sub:
        return sub.plan

    name = (getattr(hostel, "plan_name", "") or "").strip()
    if name:
        return (
            Plan.objects.filter(slug__iexact=name).first()
            or Plan.objects.filter(name__iexact=name).first()
        )
    return None


# --------------------------------------------------------------------------- #
# Snapshot build (uncached)
# --------------------------------------------------------------------------- #
def _build_snapshot(hostel) -> dict:
    plan = resolve_plan(hostel)

    # Features: start from catalog defaults, layer the plan, then overrides.
    features = {}
    for f in Feature.objects.filter(is_active=True).values(
        "id", "key", "default_enabled", "release_stage"
    ):
        eligible = f["release_stage"] in _DEFAULT_ELIGIBLE_STAGES
        features[f["key"]] = {
            "id": f["id"],
            "enabled": bool(f["default_enabled"]) and eligible,
        }
    key_by_feature_id = {v["id"]: k for k, v in features.items()}

    if plan is not None:
        for pf in PlanFeature.objects.filter(plan=plan).values("feature_id", "is_enabled"):
            key = key_by_feature_id.get(pf["feature_id"])
            if key:
                features[key]["enabled"] = bool(pf["is_enabled"])

    if hostel is not None:
        now_overrides = FeatureOverride.objects.filter(hostel=hostel).select_related("feature")
        for ov in now_overrides:
            if not ov.is_live:
                continue
            key = ov.feature.key
            if key in features:
                features[key]["enabled"] = bool(ov.is_enabled)

    # Limits: catalog default, then the plan, then overrides. value None = ∞.
    limits = {}
    for ld in LimitDefinition.objects.filter(is_active=True).values(
        "id", "key", "default_value"
    ):
        limits[ld["key"]] = {"id": ld["id"], "value": int(ld["default_value"])}
    key_by_limit_id = {v["id"]: k for k, v in limits.items()}

    if plan is not None:
        for pl in PlanLimit.objects.filter(plan=plan).values(
            "limit_id", "value", "is_unlimited"
        ):
            key = key_by_limit_id.get(pl["limit_id"])
            if key:
                limits[key]["value"] = None if pl["is_unlimited"] else int(pl["value"])

    if hostel is not None:
        for ov in LimitOverride.objects.filter(hostel=hostel).select_related("limit"):
            if not ov.is_live:
                continue
            key = ov.limit.key
            if key in limits:
                limits[key]["value"] = None if ov.is_unlimited else int(ov.value)

    return {
        "plan": (
            {"id": str(plan.pk), "name": plan.name, "slug": plan.slug} if plan else None
        ),
        "features": {k: v["enabled"] for k, v in features.items()},
        "limits": {k: v["value"] for k, v in limits.items()},
    }


def snapshot(hostel) -> dict:
    """Cached entitlement snapshot for a hostel."""
    if hostel is None:
        return {"plan": None, "features": {}, "limits": {}}

    key = _KEY.format(gen=generation(), hostel_id=str(hostel.pk))
    try:
        hit = cache.get(key)
    except Exception:
        hit = None
    if hit is not None:
        return hit

    data = _build_snapshot(hostel)
    try:
        cache.set(key, data, _ttl())
    except Exception:
        logger.warning("entitlement cache write failed for %s", key, exc_info=True)
    return data


# --------------------------------------------------------------------------- #
# Public facade
# --------------------------------------------------------------------------- #
class Entitlements:
    """Ergonomic wrapper around a hostel's resolved snapshot.

        ent = Entitlements(request.hostel)
        if not ent.can_use("ai_reports"): ...
        limit = ent.limit("max_students")   # int, or None for unlimited
    """

    def __init__(self, hostel):
        self.hostel = hostel
        self._snap = snapshot(hostel)

    @property
    def plan(self):
        return self._snap.get("plan")

    def can_use(self, feature_key: str) -> bool:
        if not _enforced():
            return True
        return bool(self._snap.get("features", {}).get(feature_key, False))

    def limit(self, limit_key: str):
        """Resolved quota; ``None`` = unlimited, missing key -> 0."""
        if not _enforced():
            return None  # unlimited
        limits = self._snap.get("limits", {})
        return limits.get(limit_key, 0)

    def is_unlimited(self, limit_key: str) -> bool:
        if not _enforced():
            return True
        return self._snap.get("limits", {}).get(limit_key, 0) is None

    def as_dict(self) -> dict:
        return self._snap
