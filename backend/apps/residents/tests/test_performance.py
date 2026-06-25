"""Lightweight performance guards (Phase 10 §9).

Not load tests — they assert the query count stays bounded as data grows, so a
future change that reintroduces an N+1 fails CI.
"""
import datetime as dt
from decimal import Decimal

import pytest

from apps.billing.models import MonthlyDue, Payment
from apps.billing.services import recalc_due_paid_amount
from apps.residents.models import BedAssignmentHistory, Resident

RESIDENTS = "/api/residents/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client(auth_client, make_user, hostel):
    return auth_client(make_user(role="WARDEN", hostel=hostel), hostel)


def test_resident_list_has_no_n_plus_one(staff_client, hostel, django_assert_max_num_queries):
    """Listing residents (with nested bed_history) must not scale queries with N."""
    residents = [Resident(hostel=hostel, full_name=f"R{i}", join_date=dt.date.today()) for i in range(30)]
    Resident.objects.bulk_create(residents)
    # Give each a bed-history row so the nested serializer actually has rows to load.
    from conftest import BedFactory

    bed = BedFactory(hostel=hostel)
    BedAssignmentHistory.objects.bulk_create(
        [BedAssignmentHistory(hostel=hostel, resident=r, bed=bed) for r in Resident.objects.all()]
    )

    # A constant query budget regardless of row count (auth + count + page +
    # prefetch). Generous ceiling that still fails on a per-row N+1 (30+ rows).
    with django_assert_max_num_queries(15):
        resp = staff_client.get(RESIDENTS)
    assert resp.status_code == 200


def test_bulk_payment_recalc_stays_correct(hostel, resident):
    """Many payments against one due recalc to the exact sum."""
    due = MonthlyDue.objects.create(
        hostel=hostel, resident=resident, year=2026, month=6, amount=Decimal("100000")
    )
    Payment.objects.bulk_create(
        [Payment(hostel=hostel, resident=resident, due=due, amount=Decimal("100")) for _ in range(50)]
    )
    recalc_due_paid_amount(due)
    due.refresh_from_db()
    assert due.paid_amount == Decimal("5000")  # 50 * 100


def test_bulk_resident_creation(hostel):
    Resident.objects.bulk_create(
        [Resident(hostel=hostel, full_name=f"Bulk{i}", join_date=dt.date.today()) for i in range(200)]
    )
    assert Resident.objects.filter(hostel=hostel).count() == 200
