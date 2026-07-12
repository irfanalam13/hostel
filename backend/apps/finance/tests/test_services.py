"""Finance service-layer tests: invoice math, document numbering, payment
settlement, refunds and the ledger."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.finance import services
from apps.finance.models import (
    Discount,
    ExpenseCategory,
    FeeCategory,
    Invoice,
    LedgerTransaction,
    PaymentRecord,
    Refund,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(make_user, hostel):
    return make_user(role="ACCOUNTANT", hostel=hostel)


def _invoice(hostel, user, resident, **kwargs):
    defaults = dict(
        lines=[{"description": "Hostel fee", "quantity": "1", "unit_price": "5000.00"}],
    )
    defaults.update(kwargs)
    return services.create_invoice(hostel=hostel, actor=user, resident=resident, **defaults)


class TestDocumentNumbers:
    def test_sequential_numbers_per_hostel(self, hostel, user, resident):
        inv1 = _invoice(hostel, user, resident)
        inv2 = _invoice(hostel, user, resident)
        assert inv1.number == "INV-000001"
        assert inv2.number == "INV-000002"

    def test_sequences_are_tenant_isolated(self, hostel, other_hostel, user, resident):
        from conftest import ResidentFactory

        _invoice(hostel, user, resident)
        other_resident = ResidentFactory(hostel=other_hostel)
        other_inv = services.create_invoice(
            hostel=other_hostel, actor=user, resident=other_resident,
            lines=[{"description": "Fee", "unit_price": "100.00"}],
        )
        assert other_inv.number == "INV-000001"


class TestInvoiceMath:
    def test_line_tax_and_totals(self, hostel, user, resident):
        invoice = _invoice(
            hostel, user, resident,
            lines=[
                {"description": "Room", "quantity": "2", "unit_price": "1500.00", "tax_rate": "13"},
                {"description": "Mess", "unit_price": "2000.00"},
            ],
        )
        assert invoice.subtotal == Decimal("5000.00")
        assert invoice.tax_total == Decimal("390.00")  # 13% of 3000
        assert invoice.total == Decimal("5390.00")
        assert invoice.status == Invoice.Status.PENDING

    def test_discount_adjustment_derived_from_definition(self, hostel, user, resident):
        discount = Discount.objects.create(
            hostel=hostel, name="Early bird", discount_type="percentage", value=Decimal("10"),
        )
        invoice = _invoice(
            hostel, user, resident,
            lines=[{"description": "Fee", "unit_price": "1000.00"}],
            adjustments=[{"kind": "discount", "discount": discount}],
        )
        assert invoice.discount_total == Decimal("100.00")
        assert invoice.total == Decimal("900.00")
        discount.refresh_from_db()
        assert discount.used_count == 1

    def test_concessions_never_push_total_negative(self, hostel, user, resident):
        invoice = _invoice(
            hostel, user, resident,
            lines=[{"description": "Fee", "unit_price": "100.00"}],
            adjustments=[{"kind": "waiver", "amount": "500.00"}],
        )
        assert invoice.total == Decimal("0.00")


class TestPaymentSettlement:
    def test_settle_marks_paid_and_posts_ledger(self, hostel, user, resident):
        invoice = _invoice(hostel, user, resident)
        payment = PaymentRecord.objects.create(
            hostel=hostel, invoice=invoice, resident=resident,
            amount=Decimal("5000.00"), status=PaymentRecord.Status.PENDING,
        )
        services.settle_payment(payment, verified_by=user)

        payment.refresh_from_db()
        invoice.refresh_from_db()
        assert payment.status == PaymentRecord.Status.VERIFIED
        assert payment.receipt_number.startswith("RCT-")
        assert invoice.paid_amount == Decimal("5000.00")
        assert invoice.status == Invoice.Status.PAID
        txn = LedgerTransaction.objects.get(entity_id=str(payment.id))
        assert txn.direction == LedgerTransaction.Direction.IN
        assert txn.amount == Decimal("5000.00")

    def test_partial_payment_status(self, hostel, user, resident):
        invoice = _invoice(hostel, user, resident)
        payment = PaymentRecord.objects.create(
            hostel=hostel, invoice=invoice, amount=Decimal("2000.00"),
            status=PaymentRecord.Status.PENDING,
        )
        services.settle_payment(payment)
        invoice.refresh_from_db()
        assert invoice.status == Invoice.Status.PARTIAL
        assert invoice.balance == Decimal("3000.00")

    def test_void_backs_out_of_ledger_and_invoice(self, hostel, user, resident):
        invoice = _invoice(hostel, user, resident)
        payment = PaymentRecord.objects.create(
            hostel=hostel, invoice=invoice, amount=Decimal("5000.00"),
            status=PaymentRecord.Status.PENDING,
        )
        services.settle_payment(payment)
        services.void_payment(payment, status=PaymentRecord.Status.CANCELLED)

        invoice.refresh_from_db()
        assert invoice.paid_amount == Decimal("0.00")
        assert invoice.status == Invoice.Status.PENDING
        assert not LedgerTransaction.objects.filter(entity_id=str(payment.id)).exists()

    def test_settle_is_idempotent(self, hostel, user, resident):
        invoice = _invoice(hostel, user, resident)
        payment = PaymentRecord.objects.create(
            hostel=hostel, invoice=invoice, amount=Decimal("5000.00"),
            status=PaymentRecord.Status.PENDING,
        )
        services.settle_payment(payment)
        first_receipt = payment.receipt_number
        services.settle_payment(payment)
        assert payment.receipt_number == first_receipt
        assert LedgerTransaction.objects.filter(entity_id=str(payment.id)).count() == 1


class TestRefunds:
    def test_process_posts_out_and_flips_full_refund(self, hostel, user, resident):
        invoice = _invoice(hostel, user, resident)
        payment = PaymentRecord.objects.create(
            hostel=hostel, invoice=invoice, resident=resident,
            amount=Decimal("5000.00"), status=PaymentRecord.Status.PENDING,
        )
        services.settle_payment(payment)
        refund = Refund.objects.create(
            hostel=hostel, payment=payment, resident=resident,
            amount=Decimal("5000.00"), reason="Withdrawal",
            status=Refund.Status.APPROVED,
        )
        services.process_refund(refund, actor=user)

        refund.refresh_from_db()
        payment.refresh_from_db()
        assert refund.status == Refund.Status.PROCESSED
        assert payment.status == PaymentRecord.Status.REFUNDED
        txn = LedgerTransaction.objects.get(entity_id=str(refund.id))
        assert txn.direction == LedgerTransaction.Direction.OUT


class TestOverdueAndSeeds:
    def test_refresh_overdue_flips_past_due(self, hostel, user, resident):
        invoice = _invoice(
            hostel, user, resident,
            due_date=timezone.localdate() - timedelta(days=3),
        )
        # create_invoice recalc already applies overdue based on due_date
        assert invoice.status == Invoice.Status.OVERDUE

        future = _invoice(
            hostel, user, resident,
            due_date=timezone.localdate() + timedelta(days=3),
        )
        assert future.status == Invoice.Status.PENDING

    def test_default_categories_seed_once(self, hostel):
        services.ensure_default_categories(hostel)
        fee_count = FeeCategory.objects.filter(hostel=hostel).count()
        exp_count = ExpenseCategory.objects.filter(hostel=hostel).count()
        services.ensure_default_categories(hostel)
        assert FeeCategory.objects.filter(hostel=hostel).count() == fee_count
        assert ExpenseCategory.objects.filter(hostel=hostel).count() == exp_count
        assert fee_count > 0 and exp_count > 0
