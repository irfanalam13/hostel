import datetime as dt
from decimal import Decimal

from django.test import TestCase

from apps.tenants.models import Hostel
from apps.students.models import Student
from apps.fees.models import FeeLedger
from apps.payments.models import Payment, Receipt
from apps.payments.services import allocate_payment


class AllocatePaymentTests(TestCase):
    def setUp(self):
        self.hostel = Hostel.objects.create(name="Test Hostel")
        self.other_hostel = Hostel.objects.create(name="Other Hostel")
        self.student = Student.objects.create(
            hostel=self.hostel, full_name="Asha", phone="111", join_date=dt.date.today()
        )
        self.other_student = Student.objects.create(
            hostel=self.hostel, full_name="Bibek", phone="222", join_date=dt.date.today()
        )
        self.ledger = FeeLedger.objects.create(
            hostel=self.hostel, student=self.student, month="2026-06",
            amount=Decimal("500"), net_due=Decimal("500"),
        )

    def _payment(self, student, amount):
        return Payment.objects.create(
            hostel=self.hostel, student=student, amount=Decimal(amount),
            date=dt.date.today(),
        )

    def test_valid_full_allocation_marks_paid_and_creates_receipt(self):
        payment = self._payment(self.student, "500")
        allocate_payment(self.hostel, payment, [
            {"ledger_id": str(self.ledger.id), "amount": "500"},
        ])
        self.ledger.refresh_from_db()
        self.assertEqual(self.ledger.status, "PAID")
        self.assertTrue(Receipt.objects.filter(payment=payment).exists())

    def test_partial_allocation_marks_partial(self):
        payment = self._payment(self.student, "200")
        allocate_payment(self.hostel, payment, [
            {"ledger_id": str(self.ledger.id), "amount": "200"},
        ])
        self.ledger.refresh_from_db()
        self.assertEqual(self.ledger.status, "PARTIAL")

    def test_over_allocation_beyond_outstanding_is_rejected(self):
        payment = self._payment(self.student, "800")
        with self.assertRaises(ValueError):
            allocate_payment(self.hostel, payment, [
                {"ledger_id": str(self.ledger.id), "amount": "800"},
            ])
        self.ledger.refresh_from_db()
        self.assertEqual(self.ledger.status, "DUE")
        self.assertFalse(Receipt.objects.filter(payment=payment).exists())

    def test_cross_student_allocation_is_rejected(self):
        payment = self._payment(self.other_student, "500")
        with self.assertRaises(ValueError):
            allocate_payment(self.hostel, payment, [
                {"ledger_id": str(self.ledger.id), "amount": "500"},
            ])

    def test_negative_amount_is_rejected(self):
        payment = self._payment(self.student, "0")
        with self.assertRaises(ValueError):
            allocate_payment(self.hostel, payment, [
                {"ledger_id": str(self.ledger.id), "amount": "-50"},
            ])

    def test_total_must_equal_payment_amount(self):
        payment = self._payment(self.student, "500")
        with self.assertRaises(ValueError):
            allocate_payment(self.hostel, payment, [
                {"ledger_id": str(self.ledger.id), "amount": "300"},
            ])

    def test_duplicate_ledger_cannot_exceed_outstanding(self):
        payment = self._payment(self.student, "600")
        with self.assertRaises(ValueError):
            allocate_payment(self.hostel, payment, [
                {"ledger_id": str(self.ledger.id), "amount": "300"},
                {"ledger_id": str(self.ledger.id), "amount": "300"},
            ])

    def test_empty_allocations_rejected(self):
        payment = self._payment(self.student, "500")
        with self.assertRaises(ValueError):
            allocate_payment(self.hostel, payment, [])
