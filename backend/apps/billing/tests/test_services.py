from decimal import Decimal

from django.test import TestCase

from apps.residents.models import Resident
from apps.tenants.models import Hostel

from apps.billing.models import MonthlyDue, Payment
from apps.billing.serializers import PaymentSerializer
from apps.billing.services import recalc_due_paid_amount


class PaymentValidatorTests(TestCase):
    """C4: payments must be strictly positive (no negative/zero 'payments')."""

    def setUp(self):
        self.hostel = Hostel.objects.create(name="Test Hostel")
        self.resident = Resident.objects.create(hostel=self.hostel, full_name="Asha R.")

    def _serializer(self, amount):
        return PaymentSerializer(data={
            "resident": self.resident.id,
            "amount": amount,
            "method": "cash",
        })

    def test_zero_amount_rejected(self):
        self.assertFalse(self._serializer("0.00").is_valid())

    def test_negative_amount_rejected(self):
        self.assertFalse(self._serializer("-50.00").is_valid())

    def test_positive_amount_accepted(self):
        self.assertTrue(self._serializer("500.00").is_valid())


class RecalcDuePaidAmountTests(TestCase):
    """Locked recompute sums a due's payments into paid_amount correctly."""

    def setUp(self):
        self.hostel = Hostel.objects.create(name="Test Hostel")
        self.resident = Resident.objects.create(hostel=self.hostel, full_name="Bina K.")
        self.due = MonthlyDue.objects.create(
            hostel=self.hostel, resident=self.resident,
            year=2026, month=6, amount=Decimal("1000.00"),
        )

    def test_partial_then_full(self):
        Payment.objects.create(
            hostel=self.hostel, resident=self.resident, due=self.due, amount=Decimal("400.00")
        )
        recalc_due_paid_amount(self.due)
        self.due.refresh_from_db()
        self.assertEqual(self.due.paid_amount, Decimal("400.00"))
        self.assertEqual(self.due.remaining, Decimal("600.00"))

        Payment.objects.create(
            hostel=self.hostel, resident=self.resident, due=self.due, amount=Decimal("600.00")
        )
        recalc_due_paid_amount(self.due)
        self.due.refresh_from_db()
        self.assertEqual(self.due.paid_amount, Decimal("1000.00"))
        self.assertEqual(self.due.remaining, 0)

    def test_overpayment_clamps_remaining_to_zero(self):
        Payment.objects.create(
            hostel=self.hostel, resident=self.resident, due=self.due, amount=Decimal("1200.00")
        )
        recalc_due_paid_amount(self.due)
        self.due.refresh_from_db()
        self.assertEqual(self.due.paid_amount, Decimal("1200.00"))
        self.assertEqual(self.due.remaining, 0)
