"""Finance domain services — the single place money math and lifecycle
transitions happen.

Views validate + authorize; these functions compute totals, mint document
numbers, apply payments and post ledger transactions, all inside DB
transactions so concurrent collection can't corrupt an invoice's rollups.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    DocumentSequence,
    ExpenseCategory,
    FeeCategory,
    Invoice,
    InvoiceAdjustment,
    InvoiceLine,
    LedgerTransaction,
    PaymentRecord,
    Refund,
)

TWO_PLACES = Decimal("0.01")

# Seeded per workspace on first use; workspaces add their own on top.
DEFAULT_FEE_CATEGORIES = [
    "Admission Fee", "Hostel Fee", "Room Fee", "Bed Fee", "Monthly Fee",
    "Semester Fee", "Security Deposit", "Laundry Fee", "Electricity Charge",
    "Water Charge", "Internet Fee", "Mess Fee", "Transport Fee", "Library Fee",
    "Maintenance Fee", "Late Fine", "Penalty",
]

DEFAULT_EXPENSE_CATEGORIES = [
    "Staff Salary", "Food & Kitchen", "Electricity", "Water", "Internet",
    "Maintenance", "Furniture", "Cleaning", "Laundry", "Security", "Fuel",
    "Marketing", "Office Supplies", "Repairs", "Rent", "Tax", "Insurance",
    "Miscellaneous",
]


def ensure_default_categories(hostel) -> None:
    """Idempotently seed the system fee/expense categories for a workspace."""
    for name in DEFAULT_FEE_CATEGORIES:
        FeeCategory.objects.get_or_create(
            hostel=hostel, name=name, defaults={"is_system": True}
        )
    for name in DEFAULT_EXPENSE_CATEGORIES:
        ExpenseCategory.objects.get_or_create(
            hostel=hostel, name=name, defaults={"is_system": True}
        )


def next_document_number(hostel, doc_type: str) -> str:
    """Mint the next human-facing number for a document type, atomically.

    The per-(hostel, doc_type) counter row is locked for the duration of the
    caller's transaction, so two concurrent invoices can't share a number.
    """
    prefix = {"invoice": "INV", "receipt": "RCT"}.get(doc_type, doc_type[:3].upper())
    seq, _ = DocumentSequence.objects.get_or_create(hostel=hostel, doc_type=doc_type)
    seq = DocumentSequence.objects.select_for_update().get(pk=seq.pk)
    number = seq.next_number
    seq.next_number = number + 1
    seq.save(update_fields=["next_number", "updated_at"])
    return f"{prefix}-{number:06d}"


# --------------------------------------------------------------------------- #
# Invoicing
# --------------------------------------------------------------------------- #
def _line_amounts(quantity: Decimal, unit_price: Decimal, tax_rate: Decimal):
    amount = (quantity * unit_price).quantize(TWO_PLACES)
    tax = (amount * tax_rate / Decimal("100")).quantize(TWO_PLACES)
    return amount, tax


def recalc_invoice(invoice: Invoice, *, save: bool = True) -> Invoice:
    """Recompute every rollup on an invoice from its lines, adjustments and
    verified payments, then derive the status. Cancelled/refunded/draft
    invoices keep their status (only the money fields refresh)."""
    lines = invoice.lines.all()
    subtotal = sum((line.amount for line in lines), Decimal("0.00"))
    tax_total = sum((line.tax_amount for line in lines), Decimal("0.00"))

    discount_total = Decimal("0.00")
    scholarship_total = Decimal("0.00")
    for adj in invoice.adjustments.all():
        if adj.kind == InvoiceAdjustment.Kind.SCHOLARSHIP:
            scholarship_total += adj.amount
        else:
            discount_total += adj.amount

    gross = subtotal + tax_total
    # Concessions can never push an invoice negative.
    concessions = min(discount_total + scholarship_total, gross)
    total = (gross - concessions).quantize(TWO_PLACES)

    paid = invoice.payments.filter(status=PaymentRecord.Status.VERIFIED).aggregate(
        s=Sum("amount")
    )["s"] or Decimal("0.00")

    invoice.subtotal = subtotal.quantize(TWO_PLACES)
    invoice.tax_total = tax_total.quantize(TWO_PLACES)
    invoice.discount_total = discount_total.quantize(TWO_PLACES)
    invoice.scholarship_total = scholarship_total.quantize(TWO_PLACES)
    invoice.total = total
    invoice.paid_amount = paid.quantize(TWO_PLACES)

    if invoice.status not in (
        Invoice.Status.DRAFT, Invoice.Status.CANCELLED, Invoice.Status.REFUNDED
    ):
        if paid >= total and total > 0:
            invoice.status = Invoice.Status.PAID
        elif paid > 0:
            invoice.status = Invoice.Status.PARTIAL
        elif invoice.due_date and invoice.due_date < timezone.localdate():
            invoice.status = Invoice.Status.OVERDUE
        else:
            invoice.status = Invoice.Status.PENDING

    if save:
        invoice.save(
            update_fields=[
                "subtotal", "tax_total", "discount_total", "scholarship_total",
                "total", "paid_amount", "status", "updated_at",
            ]
        )
    return invoice


@transaction.atomic
def create_invoice(*, hostel, actor, resident, lines, adjustments=None, **fields) -> Invoice:
    """Build an invoice with its lines and concession adjustments.

    ``lines``: dicts of ``description / fee_structure / quantity / unit_price /
    tax_rate``. ``adjustments``: dicts of ``kind / discount / scholarship_award /
    amount / note`` — a missing amount is derived from the linked discount or
    scholarship against the invoice's gross.
    """
    invoice = Invoice.objects.create(
        hostel=hostel,
        resident=resident,
        number=next_document_number(hostel, DocumentSequence.DocType.INVOICE),
        currency=fields.pop("currency", "") or getattr(hostel, "currency", "") or "NPR",
        created_by=actor,
        **fields,
    )

    gross = Decimal("0.00")
    for line in lines:
        quantity = Decimal(str(line.get("quantity") or "1"))
        unit_price = Decimal(str(line["unit_price"]))
        tax_rate = Decimal(str(line.get("tax_rate") or "0"))
        amount, tax = _line_amounts(quantity, unit_price, tax_rate)
        gross += amount + tax
        InvoiceLine.objects.create(
            hostel=hostel,
            invoice=invoice,
            fee_structure=line.get("fee_structure"),
            description=line["description"],
            quantity=quantity,
            unit_price=unit_price,
            tax_rate=tax_rate,
            amount=amount,
            tax_amount=tax,
        )

    for adj in adjustments or []:
        discount = adj.get("discount")
        award = adj.get("scholarship_award")
        amount = adj.get("amount")
        if amount in (None, ""):
            if discount is not None:
                amount = discount.amount_for(gross)
            elif award is not None:
                amount = award.scholarship.amount_for(gross)
            else:
                continue
        amount = Decimal(str(amount))
        if amount <= 0:
            continue
        InvoiceAdjustment.objects.create(
            hostel=hostel,
            invoice=invoice,
            kind=adj["kind"],
            discount=discount,
            scholarship_award=award,
            amount=amount,
            note=adj.get("note", ""),
        )
        if discount is not None:
            discount.used_count = discount.used_count + 1
            discount.save(update_fields=["used_count", "updated_at"])

    return recalc_invoice(invoice)


def refresh_overdue(hostel) -> int:
    """Bulk-flip past-due open invoices to OVERDUE. Cheap enough to run on
    dashboard/list reads instead of a scheduled job."""
    return Invoice.objects.filter(
        hostel=hostel,
        status=Invoice.Status.PENDING,
        due_date__lt=timezone.localdate(),
    ).update(status=Invoice.Status.OVERDUE)


# --------------------------------------------------------------------------- #
# Ledger
# --------------------------------------------------------------------------- #
def post_transaction(
    *, hostel, direction, category, amount, method, entity_type, entity_id,
    resident=None, memo="", occurred_at=None,
) -> LedgerTransaction:
    return LedgerTransaction.objects.create(
        hostel=hostel,
        direction=direction,
        category=category,
        amount=amount,
        method=method,
        entity_type=entity_type,
        entity_id=str(entity_id),
        resident=resident,
        memo=memo,
        occurred_at=occurred_at or timezone.now(),
    )


def _remove_transaction(entity_type: str, entity_id) -> None:
    LedgerTransaction.objects.filter(
        entity_type=entity_type, entity_id=str(entity_id)
    ).delete()


# --------------------------------------------------------------------------- #
# Collection
# --------------------------------------------------------------------------- #
@transaction.atomic
def settle_payment(payment: PaymentRecord, *, verified_by=None) -> PaymentRecord:
    """Mark a payment verified: mint its receipt number, post the ledger
    transaction and refresh the linked invoice. Idempotent."""
    if payment.status == PaymentRecord.Status.VERIFIED and payment.receipt_number:
        return payment
    payment.status = PaymentRecord.Status.VERIFIED
    if not payment.receipt_number:
        payment.receipt_number = next_document_number(
            payment.hostel, DocumentSequence.DocType.RECEIPT
        )
    if verified_by is not None:
        payment.verified_by = verified_by
    payment.verified_at = timezone.now()
    payment.save(
        update_fields=["status", "receipt_number", "verified_by", "verified_at", "updated_at"]
    )

    resident = payment.resident or (payment.invoice.resident if payment.invoice_id else None)
    post_transaction(
        hostel=payment.hostel,
        direction=LedgerTransaction.Direction.IN,
        category="fee_collection",
        amount=payment.amount,
        method=payment.method,
        entity_type="finance.paymentrecord",
        entity_id=payment.id,
        resident=resident,
        memo=f"Receipt {payment.receipt_number}",
        occurred_at=payment.received_at,
    )
    if payment.invoice_id:
        recalc_invoice(payment.invoice)
    return payment


@transaction.atomic
def void_payment(payment: PaymentRecord, *, status: str) -> PaymentRecord:
    """Cancel/fail a payment. A previously verified payment is backed out of
    the ledger and its invoice rollups."""
    was_verified = payment.status == PaymentRecord.Status.VERIFIED
    payment.status = status
    payment.save(update_fields=["status", "updated_at"])
    if was_verified:
        _remove_transaction("finance.paymentrecord", payment.id)
        if payment.invoice_id:
            recalc_invoice(payment.invoice)
    return payment


# --------------------------------------------------------------------------- #
# Refunds
# --------------------------------------------------------------------------- #
@transaction.atomic
def process_refund(refund: Refund, *, actor) -> Refund:
    """Execute an approved refund: post the outward transaction and, when the
    linked payment is now fully refunded, flip payment + invoice status."""
    refund.status = Refund.Status.PROCESSED
    refund.processed_at = timezone.now()
    refund.save(update_fields=["status", "processed_at", "updated_at"])

    resident = refund.resident or (refund.payment.resident if refund.payment_id else None)
    post_transaction(
        hostel=refund.hostel,
        direction=LedgerTransaction.Direction.OUT,
        category=f"refund:{refund.refund_type}",
        amount=refund.amount,
        method=refund.method,
        entity_type="finance.refund",
        entity_id=refund.id,
        resident=resident,
        memo=refund.reason,
    )

    payment = refund.payment
    if payment is not None:
        refunded = payment.refunds.filter(status=Refund.Status.PROCESSED).aggregate(
            s=Sum("amount")
        )["s"] or Decimal("0.00")
        if refunded >= payment.amount:
            payment.status = PaymentRecord.Status.REFUNDED
            payment.save(update_fields=["status", "updated_at"])
            if payment.invoice_id:
                invoice = recalc_invoice(payment.invoice)
                if invoice.paid_amount == 0 and invoice.status == Invoice.Status.PENDING:
                    invoice.status = Invoice.Status.REFUNDED
                    invoice.save(update_fields=["status", "updated_at"])
    return refund


# --------------------------------------------------------------------------- #
# Expenses / income
# --------------------------------------------------------------------------- #
@transaction.atomic
def mark_expense_paid(expense, *, actor):
    expense.status = expense.Status.PAID
    if expense.approved_by_id is None:
        expense.approved_by = actor
        expense.approved_at = timezone.now()
    expense.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    category = expense.category.name if expense.category_id else "Uncategorized"
    post_transaction(
        hostel=expense.hostel,
        direction=LedgerTransaction.Direction.OUT,
        category=f"expense:{category}",
        amount=expense.amount + expense.tax_amount,
        method=expense.payment_method,
        entity_type="finance.expense",
        entity_id=expense.id,
        memo=expense.title,
    )
    return expense


@transaction.atomic
def record_income_transaction(income):
    post_transaction(
        hostel=income.hostel,
        direction=LedgerTransaction.Direction.IN,
        category=f"income:{income.source}",
        amount=income.amount,
        method=income.payment_method,
        entity_type="finance.income",
        entity_id=income.id,
        memo=income.title,
    )
    return income


def remove_income_transaction(income):
    _remove_transaction("finance.income", income.id)
