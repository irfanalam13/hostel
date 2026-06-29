import random
import re
import uuid
import string
from django.db import models
from apps.common.models import TimeStampedModel

HOSTEL_CODE_RE = re.compile(r"^HTL-[A-Z0-9]{8}$")



class Plan(TimeStampedModel):
    name = models.CharField(max_length=50)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_students = models.IntegerField(default=200)
    max_rooms = models.IntegerField(default=50)

    def __str__(self):
        return self.name


def generate_hostel_code():
    alphabet = string.ascii_uppercase + string.digits
    return "HTL-" + "".join(random.choices(alphabet, k=8))


class Hostel(TimeStampedModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=12, unique=True, db_index=True, blank=True)  # official Hostel ID

    address = models.CharField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    owner_name = models.CharField(max_length=80, blank=True, default="")

    is_active = models.BooleanField(default=True)

    # SaaS settings and subscription basics
    settings = models.JSONField(default=dict, blank=True)
    plan_name = models.CharField(max_length=50, default="basic")
    subscription_active_until = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            original_code = Hostel.objects.filter(pk=self.pk).values_list("code", flat=True).first()
            if original_code:
                self.code = original_code
        if not self.code:
            code = generate_hostel_code()
            while Hostel.objects.filter(code=code).exists():
                code = generate_hostel_code()
            self.code = code
        self.code = self.code.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"
    
class Subscription(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, default="active")  # active/cancelled/expired
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
