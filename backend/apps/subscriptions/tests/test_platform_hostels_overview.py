"""PlatformHostelsOverviewView — the super-admin cross-tenant business rollup.

Every hostel's OWN student/revenue/dues numbers (not the platform's SaaS
billing MRR — see AnalyticsView for that). Must be reachable only by a
platform super-admin: a tenant OWNER must never see another workspace's
business data, and this view is the only place that data is aggregated
across every tenant at once.
"""
import datetime as dt
from decimal import Decimal

import pytest

from apps.common.utils import month_key
from apps.fees.models import FeeLedger
from apps.payments.models import Payment
from apps.rooms.models import Bed, Room
from apps.students.models import Student
from apps.tenants.services import get_or_create_platform_workspace

URL = "/api/platform/hostels/overview/"

pytestmark = pytest.mark.django_db


def _make_student(hostel, *, status="ACTIVE", **kwargs):
    return Student.objects.create(
        hostel=hostel,
        full_name=kwargs.pop("full_name", "Test Student"),
        phone=kwargs.pop("phone", "9800000000"),
        join_date=kwargs.pop("join_date", dt.date(2026, 1, 1)),
        status=status,
        **kwargs,
    )


def _make_bed(hostel, *, status="AVAILABLE"):
    room = Room.objects.create(hostel=hostel, room_no=f"R-{Bed.objects.count()}")
    return Bed.objects.create(hostel=hostel, room=room, bed_no="1", status=status)


def _row_for(payload, hostel):
    return next(r for r in payload if r["id"] == str(hostel.id))


def test_superuser_sees_aggregated_metrics_per_hostel(superuser, hostel, other_hostel, auth_client):
    today = dt.date.today()

    # `hostel`: 2 active + 1 former student, 1 occupied + 1 available bed,
    # one payment this month, one outstanding fee-ledger entry this month.
    _make_student(hostel, full_name="Active One")
    _make_student(hostel, full_name="Active Two")
    _make_student(hostel, full_name="Left One", status="LEFT")
    _make_bed(hostel, status="OCCUPIED")
    _make_bed(hostel, status="AVAILABLE")
    Payment.objects.create(
        hostel=hostel,
        student=Student.objects.filter(hostel=hostel).first(),
        amount=Decimal("15000.00"),
        date=today,
    )
    due_student = Student.objects.filter(hostel=hostel).first()
    FeeLedger.objects.create(
        hostel=hostel,
        student=due_student,
        month=month_key(today),
        amount=Decimal("5000.00"),
        net_due=Decimal("5000.00"),
        status="DUE",
    )

    # `other_hostel`: a single active student, nothing else — proves the
    # zero-default path (no payments/beds/dues yet) doesn't crash or leak
    # `hostel`'s numbers onto it.
    _make_student(other_hostel, full_name="Solo Student")

    resp = auth_client(superuser, hostel).get(URL)
    assert resp.status_code == 200
    payload = resp.json()
    data = payload["data"] if isinstance(payload, dict) and "data" in payload else payload

    row = _row_for(data, hostel)
    assert row["name"] == hostel.name
    assert row["active_students"] == 2
    assert row["beds_total"] == 2
    assert row["beds_occupied"] == 1
    assert Decimal(row["month_revenue"]) == Decimal("15000.00")
    assert Decimal(row["month_due"]) == Decimal("5000.00")
    assert row["due_count"] == 1

    other_row = _row_for(data, other_hostel)
    assert other_row["active_students"] == 1
    assert other_row["beds_total"] == 0
    assert other_row["beds_occupied"] == 0
    assert Decimal(other_row["month_revenue"]) == Decimal("0")
    assert Decimal(other_row["month_due"]) == Decimal("0")
    assert other_row["due_count"] == 0

    # The `superuser` fixture is_superuser=True, which auto-creates + links
    # the hidden platform workspace (see apps.accounts.apps signal) — it must
    # never appear as a fake row in this business rollup.
    platform_hostel = get_or_create_platform_workspace()
    assert not any(r["id"] == str(platform_hostel.id) for r in data)
    assert len(data) == 2


def test_tenant_owner_cannot_see_cross_tenant_overview(owner, hostel, auth_client):
    resp = auth_client(owner, hostel).get(URL)
    assert resp.status_code == 403


def test_anonymous_denied(api):
    assert api.get(URL).status_code in (401, 403)
