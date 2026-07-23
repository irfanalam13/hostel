"""Tenant-facing entitlement API.

Exposes the resolved feature/limit snapshot for the caller's current workspace
so the frontend can gate UI, show usage meters and drive the upgrade experience
(Module 12). Read-only; Super-Admin plan management lives in a later phase.
"""
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import HasHostelContext

from .entitlements import Entitlements
from .services import plan_feature_map, plan_limit_map
from .usage import current_usage


def _plan_summary(plan) -> dict:
    return {
        "id": str(plan.pk),
        "name": plan.name,
        "slug": plan.slug,
        "description": plan.description,
        "price_monthly": str(plan.price_monthly),
        "price_yearly": str(plan.price_yearly),
        "discounted_price": str(plan.discounted_price),
        "currency": plan.currency,
        "billing_interval": plan.billing_interval,
        "badge": plan.badge,
        "is_recommended": plan.is_recommended,
        "is_featured": plan.is_featured,
    }


class EntitlementsView(APIView):
    """``GET /api/subscriptions/entitlements/`` — what this workspace can do."""

    permission_classes = [IsAuthenticated, HasHostelContext]

    @extend_schema(
        tags=["Subscriptions"],
        summary="Resolved feature/limit entitlements for the current workspace",
    )
    def get(self, request):
        hostel = getattr(request, "hostel", None)
        ent = Entitlements(hostel)
        snap = ent.as_dict()

        limits = {}
        for key, maximum in snap.get("limits", {}).items():
            used = current_usage(hostel, key)
            remaining = None
            if maximum is not None and used is not None:
                remaining = max(maximum - used, 0)
            limits[key] = {
                "max": maximum,            # None == unlimited
                "used": used,              # None == not metered at create-time
                "remaining": remaining,
                "unlimited": maximum is None,
            }

        return Response(
            {
                "plan": snap.get("plan"),
                "features": snap.get("features", {}),
                "limits": limits,
            }
        )


class AvailablePlansView(APIView):
    """``GET /api/subscriptions/plans/`` — sellable plans for a pricing/upgrade view."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Subscriptions"], summary="Sellable plans for the current tenant")
    def get(self, request):
        from apps.tenants.models import Plan, PlanVisibility

        plans = Plan.objects.filter(
            is_active=True, is_archived=False, visibility=PlanVisibility.PUBLIC
        ).order_by("sort_order", "price_monthly")
        return Response([_plan_summary(p) for p in plans])


class UpgradeOptionsView(APIView):
    """``GET /api/subscriptions/upgrade-options/?feature=<key>`` (or ``?limit=<key>&needed=<n>``)

    Returns the plans that would unlock a blocked feature / raise a limit, so the
    upgrade modal (Module 12) can say exactly where the capability lives.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Subscriptions"], summary="Plans that unlock a feature or higher limit")
    def get(self, request):
        from apps.tenants.models import Plan, PlanVisibility

        feature = request.query_params.get("feature")
        limit = request.query_params.get("limit")
        try:
            needed = int(request.query_params.get("needed", "0") or 0)
        except (TypeError, ValueError):
            needed = 0

        current = Entitlements(getattr(request, "hostel", None))
        candidates = Plan.objects.filter(
            is_active=True, is_archived=False, visibility=PlanVisibility.PUBLIC
        ).order_by("sort_order", "price_monthly")

        matches = []
        for plan in candidates:
            ok = False
            if feature:
                ok = plan_feature_map(plan).get(feature, False)
            elif limit:
                val = plan_limit_map(plan).get(limit)
                ok = val is None or val > (needed or current.limit(limit) or 0)
            if ok:
                matches.append(_plan_summary(plan))

        return Response(
            {
                "feature": feature,
                "limit": limit,
                "current_plan": current.plan,
                "plans": matches,
            }
        )
