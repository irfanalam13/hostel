from django.db import models
from apps.common.models import HostelScopedModel

class Payment(HostelScopedModel):
    student = models.ForeignKey("students.Student", on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    method = models.CharField(max_length=20, default="CASH")  # CASH/ESEWA/KHALTI/BANK
    reference_no = models.CharField(max_length=60, blank=True, default="")

class PaymentAllocation(HostelScopedModel):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="allocations")
    ledger = models.ForeignKey("fees.FeeLedger", on_delete=models.PROTECT, related_name="allocations")
    amount = models.DecimalField(max_digits=10, decimal_places=2)

class Receipt(HostelScopedModel):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="receipt")
    receipt_no = models.CharField(max_length=30, unique=True)