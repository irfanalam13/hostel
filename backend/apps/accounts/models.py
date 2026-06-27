from django.db import models
from django.contrib.auth.models import AbstractUser
from apps.common.models import TimeStampedModel

ROLE_CHOICES = [
    ("ADMIN", "Admin"),
    ("OWNER", "Owner"),
    ("MANAGER", "Manager"),
    ("STAFF", "Staff"),
    ("ACCOUNTANT", "Accountant"),
    ("WARDEN", "Warden"),
    ("RESIDENT", "Resident"),
]

class User(AbstractUser):
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="WARDEN")

class UserHostel(TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="hostel_links")
    hostel = models.ForeignKey("tenants.Hostel", on_delete=models.CASCADE, related_name="user_links")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "hostel")


class PasswordResetOTP(TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="password_reset_otps")
    otp = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        from django.utils import timezone
        from datetime import timedelta
        # Valid for 15 minutes
        return not self.is_used and (timezone.now() - self.created_at) < timedelta(minutes=15)


class SignupOTP(TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="signup_otps")
    otp = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        from django.utils import timezone
        from datetime import timedelta
        # Valid for 15 minutes
        return not self.is_used and (timezone.now() - self.created_at) < timedelta(minutes=15)

