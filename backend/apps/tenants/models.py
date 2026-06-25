import uuid
from django.db import models
from apps.common.models import TimeStampedModel
import uuid
from django.db import models
from apps.common.models import TimeStampedModel



class Plan(TimeStampedModel):
    name = models.CharField(max_length=50)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_students = models.IntegerField(default=200)
    max_rooms = models.IntegerField(default=50)

    def __str__(self):
        return self.name


def generate_hostel_code():
    # Short, readable, unique code e.g. "H-7K2Q9A"
    return "H-" + uuid.uuid4().hex[:6].upper()


class Hostel(TimeStampedModel):
    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=40, unique=True, blank=True)  # used in header

    address = models.CharField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    owner_name = models.CharField(max_length=80, blank=True, default="")

    is_active = models.BooleanField(default=True)

    # SaaS subscription basics
    plan_name = models.CharField(max_length=50, default="basic")
    subscription_active_until = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.code:
            # Ensure uniqueness even if collision happens (rare)
            code = generate_hostel_code()
            while Hostel.objects.filter(code=code).exists():
                code = generate_hostel_code()
            self.code = code
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"
    
    
    
class Subscription(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, default="active")  # active/cancelled/expired
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)