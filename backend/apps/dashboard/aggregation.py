"""Cross-tenant business-metrics aggregation.

Grouped queries (``.values("hostel").annotate(...)``) that return one row per
hostel in a single database round-trip, rather than looping and querying per
hostel. Used by the super-admin platform overview
(``apps.subscriptions.platform_views.PlatformHostelsOverviewView``) to roll up
every tenant's own student/revenue/dues numbers without an N+1 query per
tenant. ``Student``, ``Payment``, ``FeeLedger`` and ``Bed`` all inherit
``hostel`` from the same ``HostelScopedModel`` base, so the same grouping key
works uniformly across all four.

Mirrors the per-hostel aggregation already used by
``apps.dashboard.views.OwnerDashboardView`` — that view stays as-is (it's
already correct and efficient for the single-hostel case); this module is the
grouped, all-hostels counterpart.
"""
from django.db.models import Count, Q, Sum

from apps.fees.models import FeeLedger
from apps.payments.models import Payment
from apps.rooms.models import Bed
from apps.students.models import Student


def active_student_counts() -> dict:
    """``{hostel_id: active_student_count}`` for every hostel with at least one."""
    rows = (
        Student.objects.filter(status="ACTIVE")
        .values("hostel")
        .annotate(count=Count("id"))
    )
    return {row["hostel"]: row["count"] for row in rows}


def bed_occupancy() -> dict:
    """``{hostel_id: {"total": int, "occupied": int}}`` for every hostel with beds."""
    rows = Bed.objects.values("hostel").annotate(
        total=Count("id"),
        occupied=Count("id", filter=Q(status="OCCUPIED")),
    )
    return {row["hostel"]: {"total": row["total"], "occupied": row["occupied"]} for row in rows}


def month_collections(year: int, month: int) -> dict:
    """``{hostel_id: total_amount_collected}`` for the given calendar month."""
    rows = (
        Payment.objects.filter(date__year=year, date__month=month)
        .values("hostel")
        .annotate(total=Sum("amount"))
    )
    return {row["hostel"]: row["total"] or 0 for row in rows}


def month_due_totals(month_key: str) -> dict:
    """``{hostel_id: {"total": Decimal, "count": int}}`` of outstanding dues
    (DUE/PARTIAL) for the given ``YYYY-MM`` ledger month."""
    rows = (
        FeeLedger.objects.filter(month=month_key, status__in=["DUE", "PARTIAL"])
        .values("hostel")
        .annotate(total=Sum("net_due"), count=Count("id"))
    )
    return {row["hostel"]: {"total": row["total"] or 0, "count": row["count"]} for row in rows}
