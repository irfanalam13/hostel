"""Payment API → due recalculation (Phase 10 §4).

  * payment creation updates the linked due's cached paid_amount
  * partial / full / overpayment handling
  * deleting a payment recalculates the due
  * negative/zero rejected at the serializer
"""
from decimal import Decimal

import pytest

from apps.billing.models import MonthlyDue, Payment

PAYMENTS = "/api/billing/payments/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client(auth_client, make_user, hostel):
    return auth_client(make_user(role="WARDEN", hostel=hostel), hostel)


@pytest.fixture
def due(hostel, resident):
    return MonthlyDue.objects.create(
        hostel=hostel, resident=resident, year=2026, month=6, amount=Decimal("5000.00")
    )


def test_full_payment_updates_due(staff_client, resident, due):
    resp = staff_client.post(
        PAYMENTS, {"resident": resident.id, "due": due.id, "amount": "5000.00"}
    )
    assert resp.status_code == 201
    due.refresh_from_db()
    assert due.paid_amount == Decimal("5000.00")
    assert due.remaining == 0


def test_partial_payment_updates_due(staff_client, resident, due):
    staff_client.post(PAYMENTS, {"resident": resident.id, "due": due.id, "amount": "2000.00"})
    due.refresh_from_db()
    assert due.paid_amount == Decimal("2000.00")
    assert due.remaining == Decimal("3000.00")


def test_two_payments_sum_into_due(staff_client, resident, due):
    staff_client.post(PAYMENTS, {"resident": resident.id, "due": due.id, "amount": "2000.00"})
    staff_client.post(PAYMENTS, {"resident": resident.id, "due": due.id, "amount": "3000.00"})
    due.refresh_from_db()
    assert due.paid_amount == Decimal("5000.00")


def test_overpayment_recorded_but_remaining_zero(staff_client, resident, due):
    staff_client.post(PAYMENTS, {"resident": resident.id, "due": due.id, "amount": "6000.00"})
    due.refresh_from_db()
    assert due.paid_amount == Decimal("6000.00")
    assert due.remaining == 0  # never negative


def test_deleting_payment_recalculates_due(staff_client, resident, due):
    resp = staff_client.post(PAYMENTS, {"resident": resident.id, "due": due.id, "amount": "5000.00"})
    pid = resp.data["id"]
    due.refresh_from_db()
    assert due.paid_amount == Decimal("5000.00")

    assert staff_client.delete(f"{PAYMENTS}{pid}/").status_code == 204
    due.refresh_from_db()
    assert due.paid_amount == 0
    assert Payment.objects.filter(id=pid).count() == 0


@pytest.mark.parametrize("bad", ["0.00", "-100.00"])
def test_non_positive_payment_rejected(staff_client, resident, due, bad):
    resp = staff_client.post(PAYMENTS, {"resident": resident.id, "due": due.id, "amount": bad})
    assert resp.status_code == 400
    due.refresh_from_db()
    assert due.paid_amount == 0


def test_payment_list_scoped_to_hostel(staff_client, hostel, other_hostel, resident):
    from conftest import PaymentFactory, ResidentFactory

    PaymentFactory(hostel=hostel, resident=resident, amount=Decimal("100"))
    PaymentFactory(hostel=other_hostel, resident=ResidentFactory(hostel=other_hostel), amount=Decimal("999"))
    resp = staff_client.get(PAYMENTS)
    assert resp.status_code == 200
    assert resp.data["count"] == 1
