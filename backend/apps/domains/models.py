"""Custom domains — one hostname mapped to exactly one tenant.

Lifecycle: pending (added, DNS instructions shown) → verified (ownership
proven via TXT or CNAME) → active (serving traffic; SSL monitored). A domain
can also be disabled (kept but not routing) or failed (verification error;
retryable). ``is_primary`` marks the domain that replaces the workspace URL
in public links/SEO — the default workspace URL keeps working and 301s its
public site to the primary domain.
"""
import secrets

from django.db import models

from apps.common.models import TimeStampedModel


def generate_verification_token() -> str:
    return f"hostel-verify-{secrets.token_hex(16)}"


class CustomDomain(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending verification"
        VERIFIED = "verified", "Verified"
        ACTIVE = "active", "Active"
        FAILED = "failed", "Verification failed"
        DISABLED = "disabled", "Disabled"

    class SslStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        EXPIRING = "expiring", "Expiring soon"
        EXPIRED = "expired", "Expired"
        ERROR = "error", "Error"

    hostel = models.ForeignKey(
        "tenants.Hostel", on_delete=models.CASCADE, related_name="custom_domains"
    )
    # Globally unique: a hostname can belong to exactly one tenant, ever.
    domain = models.CharField(max_length=253, unique=True)

    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    is_primary = models.BooleanField(default=False)

    # Ownership verification (TXT preferred; CNAME accepted).
    verification_token = models.CharField(max_length=64, default=generate_verification_token)
    verification_method = models.CharField(max_length=8, blank=True, default="")  # txt | cname
    verified_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=200, blank=True, default="")

    # SSL monitoring (provisioning is platform-infrastructure level).
    ssl_status = models.CharField(
        max_length=10, choices=SslStatus.choices, default=SslStatus.UNKNOWN
    )
    ssl_expires_at = models.DateTimeField(null=True, blank=True)

    # Latest DNS health snapshot ({txt: bool, cname: bool, checked_at: iso}).
    dns_health = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-is_primary", "-created_at"]
        constraints = [
            # At most one primary domain per workspace (additional domains are
            # future-ready — the limit lives in plan config, not the schema).
            models.UniqueConstraint(
                fields=["hostel"],
                condition=models.Q(is_primary=True),
                name="uniq_primary_domain_per_hostel",
            ),
        ]

    def __str__(self):
        return f"{self.domain} ({self.status})"

    @property
    def is_routable(self) -> bool:
        return self.status == self.Status.ACTIVE

    @property
    def txt_record(self) -> dict:
        """The TXT record the owner adds to prove ownership."""
        return {
            "type": "TXT",
            "host": f"_hostel-verify.{self.domain}",
            "value": self.verification_token,
        }

    @property
    def cname_record(self) -> dict:
        """The CNAME alternative: point the domain at the workspace host."""
        from django.conf import settings

        base = getattr(settings, "TENANT_BASE_DOMAIN", "localhost")
        return {
            "type": "CNAME",
            "host": self.domain,
            "value": f"{self.hostel.slug}.{base}",
        }
