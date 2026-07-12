"""Enforcement helpers wiring the entitlement engine into request handling
(Modules 10 & 11).

Feature gate — a DRF permission that 403s (with structured upgrade context) when
the workspace's plan doesn't include a feature::

    permission_classes = [IsAuthenticated, HasHostelContext, RequiresFeature("ai_reports")]

Limit gate — a call inside ``perform_create`` that blocks resource creation once
the plan's quota is reached::

    def perform_create(self, serializer):
        enforce_limit(self.request.hostel, "max_rooms")
        serializer.save(hostel=self.request.hostel)
"""
from rest_framework.permissions import BasePermission

from .entitlements import Entitlements
from .exceptions import FeatureNotAvailable, PlanLimitExceeded
from .usage import current_usage


def _feature_label(feature_key: str) -> str:
    from .models import Feature

    f = Feature.objects.filter(key=feature_key).values("display_name", "name").first()
    if not f:
        return feature_key
    return f["display_name"] or f["name"] or feature_key


def _limit_label(limit_key: str) -> str:
    from .models import LimitDefinition

    name = LimitDefinition.objects.filter(key=limit_key).values_list("name", flat=True).first()
    return name or limit_key


def enforce_feature(hostel, feature_key: str) -> None:
    """Raise :class:`FeatureNotAvailable` unless the hostel's plan enables it."""
    if not Entitlements(hostel).can_use(feature_key):
        raise FeatureNotAvailable(feature_key, _feature_label(feature_key))


def enforce_limit(hostel, limit_key: str, *, adding: int = 1) -> None:
    """Raise :class:`PlanLimitExceeded` if creating ``adding`` more would exceed
    the plan's quota.

    No-ops when the quota is unlimited or the resource isn't countable (metered
    quotas are enforced by the metering system, not here).
    """
    maximum = Entitlements(hostel).limit(limit_key)
    if maximum is None:  # unlimited
        return
    usage = current_usage(hostel, limit_key)
    if usage is None:  # not countable at create-time
        return
    if usage + adding > maximum:
        raise PlanLimitExceeded(limit_key, _limit_label(limit_key), usage, maximum)


def RequiresFeature(*feature_keys: str):
    """DRF permission-class factory: the workspace's plan must enable EVERY
    listed feature. Raises the structured 403 so clients get upgrade context."""

    class _RequiresFeature(BasePermission):
        required_features = feature_keys

        def has_permission(self, request, view):
            hostel = getattr(request, "hostel", None)
            ent = Entitlements(hostel)
            for key in self.required_features:
                if not ent.can_use(key):
                    raise FeatureNotAvailable(key, _feature_label(key))
            return True

    _RequiresFeature.__name__ = f"RequiresFeature({', '.join(feature_keys)})"
    return _RequiresFeature
