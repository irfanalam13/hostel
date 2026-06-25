"""MonthlyDue integrity + API (Phase 10 §4).

  * one due per (resident, year, month) — no duplicate invoices
  * positive-amount enforcement
  * remaining never negative (overpayment clamps to zero)
"""
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.billing.models import MonthlyDue

DUES = "/api/billing/dues/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client(auth_client, make_user, hostel):
    return auth_client(make_user(role="WARDEN", hostel=hostel), hostel)


def test_duplicate_due_for_same_month_rejected(hostel, resident):
    MonthlyDue.objects.create(hostel=hostel, resident=resident, year=2026, month=6, amount=Decimal("5000"))
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            MonthlyDue.objects.create(hostel=hostel, resident=resident, year=2026, month=6, amount=Decimal("5000"))


def test_same_resident_different_month_allowed(hostel, resident):
    MonthlyDue.objects.create(hostel=hostel, resident=resident, year=2026, month=6, amount=Decimal("5000"))
    MonthlyDue.objects.create(hostel=hostel, resident=resident, year=2026, month=7, amount=Decimal("5000"))
    assert MonthlyDue.objects.filter(resident=resident).count() == 2


def test_remaining_clamps_to_zero_on_overpayment(hostel, resident):
    due = MonthlyDue.objects.create(
        hostel=hostel, resident=resident, year=2026, month=6,
        amount=Decimal("5000"), paid_amount=Decimal("6000"),
    )
    assert due.remaining == 0


def test_remaining_partial(hostel, resident):
    due = MonthlyDue.objects.create(
        hostel=hostel, resident=resident, year=2026, month=6,
        amount=Decimal("5000"), paid_amount=Decimal("2000"),
    )
    assert due.remaining == Decimal("3000")


def test_create_due_via_api_scopes_hostel(staff_client, hostel, resident):
    resp = staff_client.post(DUES, {"resident": resident.id, "year": 2026, "month": 8, "amount": "5000.00"})
    assert resp.status_code == 201
    due = MonthlyDue.objects.get(resident=resident, month=8)
    assert due.hostel_id == hostel.id
    # paid_amount is read-only and starts at zero.
    assert due.paid_amount == 0


def test_zero_amount_due_rejected_by_validator(staff_client, resident):
    resp = staff_client.post(DUES, {"resident": resident.id, "year": 2026, "month": 9, "amount": "0.00"})
    assert resp.status_code == 400
