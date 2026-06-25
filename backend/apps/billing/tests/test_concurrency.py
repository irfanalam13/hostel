"""Concurrency / race-condition guards (Phase 10 §6).

NOTE on the DB: the test suite runs on SQLite, where ``select_for_update`` is a
no-op and a shared in-memory DB isn't visible across threads, so these tests
assert the *correctness invariants* the locking/constraints are there to
protect rather than spawning real parallel transactions. The production target
(Postgres) enforces the row lock in ``recalc_due_paid_amount`` for true
parallelism; here we prove:

  * duplicate due generation is impossible (DB unique constraint)
  * recalc is idempotent and always reflects the true sum of payments
    (so two payment recordings can't leave a stale/clobbered paid_amount)
  * a payment recalc derives paid_amount from the payment rows, never by
    blind increment (the failure mode a race would cause)
"""
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.billing.models import MonthlyDue, Payment
from apps.billing.services import recalc_due_paid_amount

pytestmark = [pytest.mark.django_db, pytest.mark.concurrency]


@pytest.fixture
def due(hostel, resident):
    return MonthlyDue.objects.create(
        hostel=hostel, resident=resident, year=2026, month=6, amount=Decimal("5000")
    )


def test_double_due_generation_prevented(hostel, resident):
    """Two attempts to bill the same month can't both succeed."""
    MonthlyDue.objects.create(hostel=hostel, resident=resident, year=2026, month=6, amount=Decimal("5000"))
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            MonthlyDue.objects.create(hostel=hostel, resident=resident, year=2026, month=6, amount=Decimal("5000"))


def test_recalc_is_idempotent(hostel, resident, due):
    Payment.objects.create(hostel=hostel, resident=resident, due=due, amount=Decimal("2000"))
    recalc_due_paid_amount(due)
    recalc_due_paid_amount(due)  # running twice must not double-count
    due.refresh_from_db()
    assert due.paid_amount == Decimal("2000")


def test_recalc_reflects_true_payment_sum_not_increment(hostel, resident, due):
    """Simulate interleaved payments: recalc always re-derives from rows.

    Even if both 'concurrent' payments existed before either recalc ran, each
    recalc reads the full set, so the final paid_amount is the true total — the
    classic lost-update bug cannot occur.
    """
    Payment.objects.create(hostel=hostel, resident=resident, due=due, amount=Decimal("2000"))
    Payment.objects.create(hostel=hostel, resident=resident, due=due, amount=Decimal("3000"))
    # Two recalcs, as two payment handlers would each fire.
    recalc_due_paid_amount(due)
    recalc_due_paid_amount(due)
    due.refresh_from_db()
    assert due.paid_amount == Decimal("5000")


def test_deleting_one_of_two_payments_recalcs_correctly(hostel, resident, due):
    p1 = Payment.objects.create(hostel=hostel, resident=resident, due=due, amount=Decimal("2000"))
    Payment.objects.create(hostel=hostel, resident=resident, due=due, amount=Decimal("3000"))
    recalc_due_paid_amount(due)

    p1.delete()
    recalc_due_paid_amount(due)
    due.refresh_from_db()
    assert due.paid_amount == Decimal("3000")
