"""Super-Admin hostel drill-down (Overview/Students/Staff/Rooms tabs).

Strictly read-only: every view here defines ``get()`` only. No
``post``/``put``/``patch``/``delete`` handler exists on any class, so DRF's
default ``APIView`` dispatch returns 405 Method Not Allowed for those verbs
automatically — read-only is enforced by the absence of handlers, not by
convention. Gated by :class:`IsPlatformAdmin` exactly like every other
``/api/platform/`` view.

Queries the same "Track B" models (``Student``/``FeeLedger``/``Bed``/
``Payment``) that ``apps.dashboard.aggregation`` already uses for
:class:`~apps.subscriptions.platform_views.PlatformHostelsOverviewView`, so
numbers here stay consistent with the existing cross-tenant overview rollup.
"""
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.utils import month_key
from apps.fees.models import FeeLedger
from apps.payments.models import Payment
from apps.rooms.models import Bed, BedAssignment, Room
from apps.staff.models import StaffProfile
from apps.students.models import Student
from apps.tenants.models import Hostel

from . import lifecycle
from .permissions import IsPlatformAdmin
from .platform_views import PLATFORM_TAGS, _limit_rows


class PlatformHostelScopedView(APIView):
    """Base: super-admin only; resolves the ``id`` path segment to a real,
    non-deleted, non-platform-workspace hostel once for every subclass."""

    permission_classes = [IsPlatformAdmin]

    def get_hostel(self, id):
        return get_object_or_404(
            Hostel.objects.select_related("plan"),
            pk=id, is_deleted=False, is_platform_workspace=False,
        )


@extend_schema(tags=PLATFORM_TAGS)
class PlatformHostelDetailView(PlatformHostelScopedView):
    """Overview tab: basic info, plan & subscription, revenue summary, usage & limits."""

    def get(self, request, id):
        h = self.get_hostel(id)
        today = timezone.localdate()
        mkey = month_key(today)

        month_revenue = Payment.objects.filter(
            hostel=h, date__year=today.year, date__month=today.month,
        ).aggregate(total=Sum("amount"))["total"] or 0
        due_agg = FeeLedger.objects.filter(
            hostel=h, month=mkey, status__in=["DUE", "PARTIAL"],
        ).aggregate(total=Sum("net_due"), count=Count("id"))

        return Response({
            "id": str(h.pk),
            "name": h.name,
            "code": h.code,
            "status": h.status,
            "owner_name": h.owner_name or "",
            "owner_email": h.owner.email if h.owner_id else "",
            "phone": h.phone,
            "address": h.address,
            "timezone": h.timezone,
            "currency": h.currency,
            "created_at": h.created_at,
            "trial_ends_at": h.trial_ends_at,
            "plan": (
                {
                    "id": str(h.plan_id),
                    "name": h.plan.name,
                    "slug": h.plan.slug,
                    "price_monthly": str(h.plan.price_monthly),
                    "billing_interval": h.plan.billing_interval,
                }
                if h.plan_id else None
            ),
            "plan_name": h.plan.name if h.plan_id else (h.plan_name or None),
            "subscription_active_until": h.subscription_active_until,
            "mrr": str(lifecycle.monthly_equivalent(h.plan)) if h.plan_id else "0",
            "revenue_summary": {
                "month_revenue": str(month_revenue),
                "month_due": str(due_agg["total"] or 0),
                "due_count": due_agg["count"] or 0,
            },
            "usage": {
                "active_students": Student.objects.filter(hostel=h, status="ACTIVE").count(),
                "beds_total": Bed.objects.filter(hostel=h).count(),
                "beds_occupied": Bed.objects.filter(hostel=h, status="OCCUPIED").count(),
                "staff_count": StaffProfile.objects.filter(hostel=h, is_deleted=False).count(),
            },
            "plan_limits": _limit_rows(h.plan) if h.plan_id else [],
        })


@extend_schema(tags=PLATFORM_TAGS)
class PlatformHostelStudentsView(PlatformHostelScopedView):
    """Students tab: read-only roster with current room/bed + this-month due status."""

    def get(self, request, id):
        h = self.get_hostel(id)
        students = list(Student.objects.filter(hostel=h).order_by("full_name"))
        ids = [s.pk for s in students]

        beds_by_student = {
            row["student"]: {"room_no": row["bed__room__room_no"], "bed_no": row["bed__bed_no"]}
            for row in BedAssignment.objects.filter(
                hostel=h, is_active=True, student_id__in=ids
            ).values("student", "bed__bed_no", "bed__room__room_no")
        }
        mkey = month_key(timezone.localdate())
        current_ledger = {
            row["student"]: row
            for row in FeeLedger.objects.filter(
                hostel=h, month=mkey, student_id__in=ids
            ).values("student", "status", "net_due")
        }
        outstanding = {
            row["student"]: row["total"]
            for row in FeeLedger.objects.filter(
                hostel=h, student_id__in=ids, status__in=["DUE", "PARTIAL"],
            ).values("student").annotate(total=Sum("net_due"))
        }

        rows = []
        for s in students:
            bed = beds_by_student.get(s.pk, {})
            current = current_ledger.get(s.pk, {})
            rows.append({
                "id": str(s.pk),
                "full_name": s.full_name,
                "phone": s.phone,
                "status": s.status,
                "join_date": s.join_date,
                "gender": s.gender,
                "room_no": bed.get("room_no"),
                "bed_no": bed.get("bed_no"),
                "current_month_status": current.get("status"),
                "current_month_due": str(current.get("net_due") or 0),
                "total_outstanding": str(outstanding.get(s.pk) or 0),
            })
        return Response(rows)


@extend_schema(tags=PLATFORM_TAGS)
class PlatformHostelStudentDuesView(PlatformHostelScopedView):
    """Monthly due history for a single student, fetched on demand from the
    roster (kept out of the list payload above to keep that query cheap)."""

    def get(self, request, id, student_id):
        h = self.get_hostel(id)
        # Explicit hostel scoping: a student id from a DIFFERENT hostel must
        # 404, not leak that hostel's fee history.
        student = get_object_or_404(Student, pk=student_id, hostel=h)
        ledgers = FeeLedger.objects.filter(hostel=h, student=student).order_by("-month")
        return Response([
            {
                "month": ledger.month,
                "amount": str(ledger.amount),
                "discount": str(ledger.discount),
                "fine": str(ledger.fine),
                "net_due": str(ledger.net_due),
                "status": ledger.status,
                "notes": ledger.notes,
            }
            for ledger in ledgers
        ])


@extend_schema(tags=PLATFORM_TAGS)
class PlatformHostelStaffView(PlatformHostelScopedView):
    """Staff tab: read-only staff directory."""

    def get(self, request, id):
        h = self.get_hostel(id)
        staff = (
            StaffProfile.objects.filter(hostel=h, is_deleted=False)
            .select_related("user", "department", "designation", "role")
            .order_by("-created_at")
        )
        return Response([
            {
                "id": str(sp.pk),
                "employee_id": sp.employee_id,
                "full_name": sp.full_name,
                "email": sp.user.email if sp.user_id else "",
                "username": sp.user.username if sp.user_id else "",
                "phone": sp.phone,
                "account_role": sp.user.role if sp.user_id else "",
                "department_name": sp.department.name if sp.department_id else None,
                "designation_title": sp.designation.title if sp.designation_id else None,
                "role_name": sp.role.name if sp.role_id else None,
                "employment_type": sp.employment_type,
                "status": sp.status,
                "joining_date": sp.joining_date,
            }
            for sp in staff
        ])


@extend_schema(tags=PLATFORM_TAGS)
class PlatformHostelRoomsView(PlatformHostelScopedView):
    """Rooms tab: read-only room/bed occupancy breakdown."""

    def get(self, request, id):
        h = self.get_hostel(id)
        rooms = (
            Room.objects.filter(hostel=h)
            .select_related("block")
            .prefetch_related("beds")
            .order_by("room_no")
        )
        rows = []
        for r in rooms:
            beds = list(r.beds.all())
            rows.append({
                "id": str(r.pk),
                "room_no": r.room_no,
                "block_name": r.block.name if r.block_id else None,
                "floor": r.floor,
                "room_type": r.room_type,
                "capacity": r.capacity,
                "rent": str(r.rent),
                "status": r.status,
                "gender_type": r.gender_type,
                "beds_total": len(beds),
                "beds_occupied": sum(1 for b in beds if b.status == "OCCUPIED"),
                "beds": [{"id": str(b.pk), "bed_no": b.bed_no, "status": b.status} for b in beds],
            })
        return Response(rows)
