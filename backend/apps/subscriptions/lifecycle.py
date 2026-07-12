"""Hostel subscription lifecycle & analytics (Modules 9 & 16).

`assign_plan` is the one entry point for changing a hostel's plan: it updates
the canonical pointers (``Hostel.plan`` / ``plan_name``), rolls the
``tenants.Subscription`` row, records an immutable ``SubscriptionEvent`` and
invalidates the entitlement cache. `analytics` computes the platform KPIs.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .entitlements import invalidate_hostel
from .models import SubscriptionEvent
from .services import plan_feature_map


def monthly_equivalent(plan) -> Decimal:
    """A plan's monthly-recurring value, normalized across billing intervals.

    Lifetime plans contribute 0 to MRR (no recurring revenue). Uses the live
    discounted monthly price where applicable.
    """
    if plan is None:
        return Decimal("0")
    bi = (plan.billing_interval or "monthly").lower()
    if bi == "lifetime":
        return Decimal("0")
    if bi == "yearly" and plan.price_yearly:
        return (Decimal(plan.price_yearly) / Decimal("12")).quantize(Decimal("0.01"))
    # monthly / quarterly / half_yearly fall back to the (discounted) monthly price.
    try:
        return Decimal(plan.discounted_price)
    except Exception:
        return Decimal(plan.price_monthly or 0)


def _classify(from_plan, to_plan) -> str:
    if from_plan is None:
        return SubscriptionEvent.Kind.ASSIGNED
    if from_plan.pk == to_plan.pk:
        return SubscriptionEvent.Kind.RENEWED
    if monthly_equivalent(to_plan) >= monthly_equivalent(from_plan):
        return SubscriptionEvent.Kind.UPGRADED
    return SubscriptionEvent.Kind.DOWNGRADED


@transaction.atomic
def assign_plan(hostel, plan, *, actor=None, kind=None, reason="", status="active",
                end_date=None):
    """Move ``hostel`` onto ``plan``, recording history. Returns the event."""
    from apps.tenants.models import Subscription

    from_plan = hostel.plan
    resolved_kind = kind or _classify(from_plan, plan)

    # Roll the current Subscription: close any open ones, open a fresh active row.
    today = timezone.localdate()
    Subscription.objects.filter(hostel=hostel, status="active").update(
        status="cancelled", end_date=today
    )
    Subscription.objects.create(
        hostel=hostel, plan=plan, status=status, start_date=today, end_date=end_date
    )

    # Canonical pointers used by the entitlement engine.
    hostel.plan = plan
    hostel.plan_name = plan.slug or plan.name
    hostel.save(update_fields=["plan", "plan_name", "updated_at"])

    event = SubscriptionEvent.objects.create(
        hostel=hostel,
        from_plan=from_plan,
        to_plan=plan,
        kind=resolved_kind,
        status_after=status,
        mrr_amount=monthly_equivalent(plan),
        reason=reason,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
    )

    invalidate_hostel(hostel)
    return event


# --------------------------------------------------------------------------- #
# Analytics (Module 16)
# --------------------------------------------------------------------------- #
def analytics() -> dict:
    from apps.tenants.models import Hostel, Plan
    from apps.tenants.models import WorkspaceStatus
    from .models import Feature

    hostels = list(
        Hostel.objects.filter(is_deleted=False).select_related("plan")
    )

    recurring_statuses = {WorkspaceStatus.ACTIVE, WorkspaceStatus.TRIAL}
    mrr = Decimal("0")
    per_plan_hostels: dict = {}
    per_plan_mrr: dict = {}
    status_counts = {"active": 0, "trial": 0, "expired": 0, "suspended": 0, "pending": 0}
    no_plan = 0

    for h in hostels:
        status_counts[h.status] = status_counts.get(h.status, 0) + 1
        if not h.plan_id:
            no_plan += 1
            continue
        per_plan_hostels[h.plan_id] = per_plan_hostels.get(h.plan_id, 0) + 1
        if h.status in recurring_statuses:
            amt = monthly_equivalent(h.plan)
            mrr += amt
            per_plan_mrr[h.plan_id] = per_plan_mrr.get(h.plan_id, Decimal("0")) + amt

    plans = list(Plan.objects.all())
    plan_distribution = [
        {
            "plan": str(p.pk),
            "name": p.name,
            "hostels": per_plan_hostels.get(p.pk, 0),
            "mrr": str(per_plan_mrr.get(p.pk, Decimal("0"))),
        }
        for p in plans
    ]
    plan_distribution.sort(key=lambda r: r["hostels"], reverse=True)

    # Feature adoption at the plan level (how many active plans enable each).
    active_plans = [p for p in plans if p.is_active and not p.is_archived]
    enable_counts: dict = {}
    for p in active_plans:
        fmap = plan_feature_map(p)
        for key, on in fmap.items():
            if on:
                enable_counts[key] = enable_counts.get(key, 0) + 1

    total_active = len(active_plans) or 1
    feature_adoption = []
    unused = []
    for f in Feature.objects.filter(is_active=True).order_by("category__sort_order", "sort_order"):
        count = enable_counts.get(f.key, 0)
        row = {
            "key": f.key,
            "name": f.label,
            "plans_enabled": count,
            "plan_percent": round(count / total_active * 100),
        }
        feature_adoption.append(row)
        if count == 0:
            unused.append({"key": f.key, "name": f.label})

    most_used = sorted(feature_adoption, key=lambda r: r["plans_enabled"], reverse=True)[:10]

    return {
        "currency": "Rs.",
        "mrr": str(mrr),
        "arr": str(mrr * 12),
        "hostels": {
            "total": len(hostels),
            "active": status_counts.get("active", 0),
            "trial": status_counts.get("trial", 0),
            "expired": status_counts.get("expired", 0),
            "suspended": status_counts.get("suspended", 0),
            "no_plan": no_plan,
        },
        "plans": {
            "total": len(plans),
            "active": len(active_plans),
            "public": sum(1 for p in plans if p.is_public and not p.is_archived),
        },
        "plan_distribution": plan_distribution,
        "feature_adoption": feature_adoption,
        "most_used_features": most_used,
        "unused_features": unused,
    }
