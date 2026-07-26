from django.db import models
from apps.common.models import HostelScopedModel

class FeePlan(HostelScopedModel):
    name = models.CharField(max_length=80)
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=2)
    includes_wifi = models.BooleanField(default=False)
    includes_food = models.BooleanField(default=False)
    includes_laundry = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

class StudentFeePlan(HostelScopedModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="fee_plans")
    fee_plan = models.ForeignKey(FeePlan, on_delete=models.PROTECT)
    start_month = models.CharField(max_length=7)  # YYYY-MM
    end_month = models.CharField(max_length=7, null=True, blank=True)  # YYYY-MM

class FeeLedger(HostelScopedModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="ledgers")
    month = models.CharField(max_length=7)  # YYYY-MM

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fine = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_due = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, default="DUE")  # DUE/PAID/PARTIAL
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("student", "month")
        indexes = [models.Index(fields=["hostel","month","status"])]