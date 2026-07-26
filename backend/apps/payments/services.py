from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.utils.crypto import get_random_string
from apps.fees.models import FeeLedger
from .models import PaymentAllocation, Receipt

def _ledger_paid(ledger: FeeLedger, exclude_payment=None):
    """Sum of allocations against a ledger, optionally excluding one payment
    (used so an in-progress payment doesn't count its own rows twice)."""
    qs = ledger.allocations.all()
    if exclude_payment is not None:
        qs = qs.exclude(payment=exclude_payment)
    return sum((a.amount for a in qs), Decimal("0"))

def _recompute_ledger_status(ledger: FeeLedger):
    paid = sum((a.amount for a in ledger.allocations.all()), Decimal("0"))
    if paid <= Decimal("0"):
        ledger.status = "DUE"
    elif paid < ledger.net_due:
        ledger.status = "PARTIAL"
    else:
        ledger.status = "PAID"
    ledger.save(update_fields=["status", "updated_at"])

def generate_receipt_no(prefix="RCPT"):
    return f"{prefix}-{get_random_string(10).upper()}"

@transaction.atomic
def allocate_payment(hostel, payment, allocations: list[dict]):
    """
    allocations = [{"ledger_id": "...", "amount": "500"}]

    Each allocation is validated so that:
      * the amount is a positive, parseable number,
      * the target ledger exists in *this* hostel (tenant isolation) and
        belongs to the same student the payment is for (no cross-student
        allocation), and
      * the allocation does not exceed the ledger's outstanding balance,
        counting prior payments and earlier rows in this same request.

    The sum of all allocations must equal the payment amount. Any violation
    raises ValueError (caught by the serializer and surfaced as a 400) and the
    surrounding transaction rolls back, so no partial writes survive.
    """
    if not allocations:
        raise ValueError("At least one allocation is required.")

    # Tracks amounts allocated to each ledger within this single call so a
    # ledger repeated across allocations cannot be over-allocated.
    allocated_this_call: dict = {}
    total = Decimal("0")

    for item in allocations:
        if not isinstance(item, dict) or "ledger_id" not in item:
            raise ValueError("Each allocation requires a 'ledger_id'.")
        if "amount" not in item:
            raise ValueError("Each allocation requires an 'amount'.")

        try:
            amt = Decimal(str(item["amount"]))
        except (InvalidOperation, TypeError):
            raise ValueError(f"Invalid allocation amount: {item['amount']!r}.")
        if amt <= Decimal("0"):
            raise ValueError("Allocation amount must be greater than zero.")

        try:
            ledger = FeeLedger.objects.select_for_update().get(
                id=item["ledger_id"], hostel=hostel
            )
        except FeeLedger.DoesNotExist:
            raise ValueError(f"Ledger {item['ledger_id']} was not found in this hostel.")

        if ledger.student_id != payment.student_id:
            raise ValueError("Cannot allocate a payment to another student's ledger.")

        prior = _ledger_paid(ledger, exclude_payment=payment)
        prior += allocated_this_call.get(ledger.id, Decimal("0"))
        outstanding = ledger.net_due - prior
        if amt > outstanding:
            raise ValueError(
                f"Allocation {amt} exceeds the outstanding balance {outstanding} "
                f"for month {ledger.month}."
            )

        PaymentAllocation.objects.create(
            hostel=hostel, payment=payment, ledger=ledger, amount=amt
        )
        allocated_this_call[ledger.id] = (
            allocated_this_call.get(ledger.id, Decimal("0")) + amt
        )
        total += amt
        _recompute_ledger_status(ledger)

    if total != payment.amount:
        # keep strict to avoid accounting mismatch
        raise ValueError("Allocated total must equal payment amount.")

    Receipt.objects.create(
        hostel=hostel,
        payment=payment,
        receipt_no=generate_receipt_no()
    )