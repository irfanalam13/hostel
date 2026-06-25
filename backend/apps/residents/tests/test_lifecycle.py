"""Resident lifecycle: admission → dues → payment → checkout → archive.

Covered (Phase 10 §5):
  * full lifecycle end-to-end
  * checkout blocked while dues are outstanding
  * forced checkout override
  * re-admission handling
  * data consistency after checkout (bed released, history closed, stay closed)
"""
from decimal import Decimal

import pytest

from apps.billing.models import MonthlyDue, Payment
from apps.residents.models import BedAssignmentHistory, Resident, Stay

RESIDENTS = "/api/residents/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client(auth_client, make_user, hostel):
    return auth_client(make_user(role="WARDEN", hostel=hostel), hostel)


def _checkout(client, rid, **data):
    return client.post(f"{RESIDENTS}{rid}/checkout/", data)


def test_full_lifecycle_admit_bill_pay_checkout(staff_client, hostel, bed):
    # 1. Admit with a bed.
    resp = staff_client.post(RESIDENTS, {"full_name": "Lifecycle Guy", "current_bed": bed.id})
    assert resp.status_code == 201
    r = Resident.objects.get(id=resp.data["id"])
    Stay.objects.create(resident=r, bed=bed, check_in=r.join_date, is_active=True)

    # 2. Generate a monthly due.
    due = MonthlyDue.objects.create(
        hostel=hostel, resident=r, year=2026, month=6, amount=Decimal("5000.00")
    )

    # 3. Pay it in full (recalc updates the cached paid_amount).
    from apps.billing.services import recalc_due_paid_amount

    Payment.objects.create(hostel=hostel, resident=r, due=due, amount=Decimal("5000.00"))
    recalc_due_paid_amount(due)
    due.refresh_from_db()
    assert due.remaining == 0

    # 4. Checkout succeeds (no outstanding dues).
    resp = _checkout(staff_client, r.id)
    assert resp.status_code == 200

    # 5. Data consistency after checkout.
    r.refresh_from_db()
    assert r.status == "left"
    assert r.leave_date is not None
    assert r.current_bed is None
    assert not Stay.objects.filter(resident=r, is_active=True).exists()
    assert not BedAssignmentHistory.objects.filter(resident=r, end_at__isnull=True).exists()


def test_checkout_blocked_with_outstanding_dues(staff_client, hostel):
    from conftest import ResidentFactory

    r = ResidentFactory(hostel=hostel)
    MonthlyDue.objects.create(
        hostel=hostel, resident=r, year=2026, month=6,
        amount=Decimal("5000.00"), paid_amount=Decimal("1000.00"),
    )
    resp = _checkout(staff_client, r.id)
    assert resp.status_code == 400
    assert resp.data["outstanding_months"] == 1
    r.refresh_from_db()
    assert r.status == "active"  # not checked out


def test_forced_checkout_overrides_dues(staff_client, hostel):
    from conftest import ResidentFactory

    r = ResidentFactory(hostel=hostel)
    MonthlyDue.objects.create(
        hostel=hostel, resident=r, year=2026, month=6,
        amount=Decimal("5000.00"), paid_amount=Decimal("0.00"),
    )
    resp = _checkout(staff_client, r.id, force="true")
    assert resp.status_code == 200
    r.refresh_from_db()
    assert r.status == "left"


def test_checkout_succeeds_when_fully_paid(staff_client, hostel):
    from conftest import ResidentFactory

    r = ResidentFactory(hostel=hostel)
    MonthlyDue.objects.create(
        hostel=hostel, resident=r, year=2026, month=6,
        amount=Decimal("5000.00"), paid_amount=Decimal("5000.00"),
    )
    assert _checkout(staff_client, r.id).status_code == 200


def test_readmission_after_checkout(staff_client, hostel, bed):
    """A left resident can be re-admitted (status back to active, new bed)."""
    from conftest import ResidentFactory

    r = ResidentFactory(hostel=hostel, status="left")
    resp = staff_client.patch(
        f"{RESIDENTS}{r.id}/", {"status": "active", "current_bed": bed.id}
    )
    assert resp.status_code == 200
    r.refresh_from_db()
    assert r.status == "active"
    assert r.current_bed_id == bed.id
    assert BedAssignmentHistory.objects.filter(resident=r, end_at__isnull=True).count() == 1
