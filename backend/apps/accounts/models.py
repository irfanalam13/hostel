from django.db import models
from django.contrib.auth.models import AbstractUser
from apps.common.models import TimeStampedModel

ROLE_CHOICES = [
    ("ADMIN", "Admin"),
    ("OWNER", "Owner"),
    ("MANAGER", "Manager"),
    ("RECEPTIONIST", "Receptionist"),
    ("STAFF", "Staff"),
    ("ACCOUNTANT", "Accountant"),
    ("WARDEN", "Warden"),
    ("STUDENT", "Student"),
    ("PARENT", "Parent"),
    ("RESIDENT", "Resident"),  # legacy pre-portal role (student-equivalent)
    ("READ_ONLY", "Read only"),
]

class User(AbstractUser):
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="WARDEN")
    # MFA architecture preparation: flag + per-user opt-in exist so enabling a
    # second factor later is additive (verification flow only), not structural.
    # Login responses already advertise `mfa_required` based on this.
    mfa_enabled = models.BooleanField(default=False)
    # Set True when an account is provisioned with a temporary / known-default
    # password (staff & team invites, student admission). The login gate reads
    # this (surfaced via /auth/me) and forces a password change on first sign-in;
    # PasswordChangeView / password-reset clear it. Owners pick their own
    # password at signup, so they are never flagged.
    must_change_password = models.BooleanField(default=False)

    @property
    def password_version(self) -> str:
        """Short fingerprint of the current password hash. Embedded in JWTs so
        a password change invalidates every previously issued token."""
        import hashlib

        return hashlib.sha256((self.password or "").encode()).hexdigest()[:12]

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
    # Keyed by email, not a user FK: signup verification happens BEFORE any
    # account exists, so we prove ownership of the email address first.
    email = models.EmailField(db_index=True)
    otp = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        from django.utils import timezone
        from datetime import timedelta
        # Valid for 15 minutes
        return not self.is_used and (timezone.now() - self.created_at) < timedelta(minutes=15)

