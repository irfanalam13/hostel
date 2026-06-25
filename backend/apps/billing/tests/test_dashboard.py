"""Billing dashboard summary (Phase 10 §4 reporting + §2 role gating)."""
from datetime import date
from decimal import Decimal

import pytest

from apps.billing.models import MonthlyDue

SUMMARY = "/api/billing/dashboard/summary/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_client(auth_client, owner, hostel):
    return auth_client(owner, hostel)


def test_summary_aggregates_current_month(owner_client, hostel):
    from conftest import ResidentFactory

    today = date.today()
    r1 = ResidentFactory(hostel=hostel, status="active")
    r2 = ResidentFactory(hostel=hostel, status="active")
    MonthlyDue.objects.create(
        hostel=hostel, resident=r1, year=today.year, month=today.month,
        amount=Decimal("5000"), paid_amount=Decimal("2000"),
    )
    MonthlyDue.objects.create(
        hostel=hostel, resident=r2, year=today.year, month=today.month,
        amount=Decimal("3000"), paid_amount=Decimal("3000"),
    )

    resp = owner_client.get(SUMMARY)
    assert resp.status_code == 200
    data = resp.data
    assert data["total_due"] == Decimal("8000")
    assert data["total_paid"] == Decimal("5000")
    assert data["pending"] == Decimal("3000")
    assert data["active_residents"] == 2


def test_summary_excludes_other_months(owner_client, hostel, resident):
    MonthlyDue.objects.create(
        hostel=hostel, resident=resident, year=2020, month=1, amount=Decimal("9999")
    )
    resp = owner_client.get(SUMMARY)
    assert resp.data["total_due"] == 0


def test_summary_blocked_for_warden(auth_client, make_user, hostel):
    warden = make_user(role="WARDEN", hostel=hostel)
    assert auth_client(warden, hostel).get(SUMMARY).status_code == 403
