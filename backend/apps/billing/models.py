from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedModel
from apps.tenants.models import Hostel
from apps.residents.models import Resident

# Money must be strictly positive for charges/payments. (Refunds/adjustments
# live on LedgerEntry, which intentionally allows signed amounts.)
POSITIVE_AMOUNT = [MinValueValidator(Decimal("0.01"))]
NON_NEGATIVE_AMOUNT = [MinValueValidator(Decimal("0.00"))]


class MonthlyDue(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name="dues")

    year = models.IntegerField()
    month = models.IntegerField()  # 1-12
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=POSITIVE_AMOUNT)

    # computed via payments; kept for fast dashboard
    paid_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=NON_NEGATIVE_AMOUNT
    )

    class Meta:
        unique_together = [("resident", "year", "month")]
        ordering = ["-year", "-month"]
        indexes = [
            models.Index(fields=["hostel", "resident"]),
            models.Index(fields=["hostel", "year", "month"]),
        ]

    @property
    def remaining(self):
        rem = self.amount - self.paid_amount
        return rem if rem > 0 else 0

class Payment(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name="payments")

    due = models.ForeignKey(
        MonthlyDue, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=POSITIVE_AMOUNT)
    method = models.CharField(max_length=30, default="cash")  # cash, bank, esewa, khalti etc
    note = models.CharField(max_length=255, blank=True)

    received_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["hostel", "resident"]),
            models.Index(fields=["due"]),
            models.Index(fields=["hostel", "received_at"]),
        ]
        
        

class Invoice(TimeStampedModel):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("partial", "Partial"),
        ("cancelled", "Cancelled"),
    )

    resident = models.ForeignKey(
        Resident,
        on_delete=models.CASCADE,
        related_name="invoices"
    )

    month = models.DateField()  # billing month
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=POSITIVE_AMOUNT)
    due_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=NON_NEGATIVE_AMOUNT
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.due_amount = self.amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.resident.full_name} - {self.month}"
    
    
class LedgerEntry(TimeStampedModel):
    ENTRY_TYPE = (
        ("payment", "Payment"),
        ("adjustment", "Adjustment"),
        ("refund", "Refund"),
    )

    resident = models.ForeignKey(
        Resident,
        on_delete=models.CASCADE,
        related_name="ledger_entries"
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE)

    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.resident.full_name} - {self.entry_type}"
    
class VacateRequest(TimeStampedModel):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    resident = models.ForeignKey(
        Resident,
        on_delete=models.CASCADE,
        related_name="vacate_requests"
    )

    requested_date = models.DateField(default=timezone.localdate)
    approved_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.resident.full_name} - Vacate"