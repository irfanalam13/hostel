from django.db import transaction
from django.db.models import Sum

from .models import MonthlyDue, Payment


def recalc_due_paid_amount(due: MonthlyDue):
    """Recompute a due's cached paid_amount from its payments.

    Locks the due row for the duration so two concurrent payment recordings
    can't both read a stale paid_amount and clobber each other's write.
    """
    with transaction.atomic():
        locked = MonthlyDue.objects.select_for_update().get(pk=due.pk)
        total = Payment.objects.filter(due=locked).aggregate(s=Sum("amount"))["s"] or 0
        locked.paid_amount = total
        locked.save(update_fields=["paid_amount", "updated_at"])
        # Keep the caller's in-memory instance consistent.
        due.paid_amount = total
    return due
