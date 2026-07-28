"""Cross-hostel discovery directory + verified-resident reviews.

Platform-level (cross-tenant), same shape as ``apps.marketing`` — NOT
tenant-scoped like most of the codebase. ``Review``/``ReviewResponse``/
``ReviewFlag`` are created from anonymous or platform-workspace-bound
requests (``request.tenant`` is None), so they deliberately do not use
``apps.common.models.HostelScopedModel`` — that base's implicit convention
elsewhere in the codebase is "created inside a ``request.hostel``-scoped
tenant route," which would be misleading here.

Not to be confused with ``apps.tenants.Testimonial`` — that model is a
customer review of the SaaS *platform itself* (shown on the marketing
landing page). ``discovery.Review`` is a resident's review of a specific
*hostel*. Keep the vocabulary and throttle scopes distinct.
"""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class ConsumerProfile(TimeStampedModel):
    """Identity data for a CONSUMER-role account (a reviewer, not staff/
    resident-portal user). Collected once at signup and reused for residency
    verification on every review the account later submits — see
    ``apps.discovery.services.apply_verification``. Kept out of ``accounts.User``
    (which every role shares) since ``phone`` here is meaningful only for this
    feature's verification matching, not a general account attribute.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consumer_profile"
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30)

    def __str__(self):
        return self.full_name


class HostelDiscoveryProfile(TimeStampedModel):
    """Directory-only presentation + rating cache for a hostel.

    Deliberately not merged into ``tenants.Hostel`` — keeps this feature's
    schema churn out of the core tenant model. ``city``/``district``/
    ``hostel_type``/``enable_public_website`` are denormalized copies of the
    corresponding ``Hostel.settings`` workspace-settings values (kept in sync
    by a signal in ``apps.website.services`` on publish/settings-save) so the
    directory listing query can filter/sort with plain indexed SQL instead of
    loading and filtering every hostel's JSON settings blob in Python.
    """

    hostel = models.OneToOneField(
        "tenants.Hostel", on_delete=models.CASCADE, related_name="discovery_profile"
    )

    # Platform-ops kill switch (fraud/abuse) — NOT a tenant opt-out. Every
    # published website is listed by default; this only ever flips false from
    # the platform side.
    is_listed = models.BooleanField(default=True)

    # Controlled vocabulary (wifi, cctv, laundry, hot_water,
    # attached_bathroom, food_included, parking, study_room, gym, ac, ...),
    # edited by tenant staff via a dedicated endpoint — never parsed from the
    # website builder's freeform facilities/amenities section content.
    amenity_tags = models.JSONField(default=list, blank=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Denormalized rating cache, recomputed by apps.discovery.tasks.recompute_hostel_rating.
    average_rating = models.DecimalField(max_digits=2, decimal_places=1, default=0, db_index=True)
    rating_count = models.PositiveIntegerField(default=0)
    rating_breakdown = models.JSONField(default=dict, blank=True)  # {"1": 0, ..., "5": 0}
    rating_computed_at = models.DateTimeField(null=True, blank=True)

    # Denormalized from Hostel.settings workspace-settings (business/profile/
    # preferences namespaces) — see module docstring.
    city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    hostel_type = models.CharField(max_length=40, blank=True, default="", db_index=True)
    enable_public_website = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "hostel discovery profile"

    def __str__(self):
        return f"DiscoveryProfile({self.hostel_id})"


class Review(TimeStampedModel):
    """A verified resident's review of a specific hostel."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending verification"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Verification rejected"
        FLAGGED = "flagged", "Flagged — under platform review"
        REMOVED = "removed", "Removed"

    class VerificationMethod(models.TextChoices):
        AUTO_PHONE_MATCH = "auto_phone", "Auto-matched by phone"
        STAFF_APPROVED = "staff", "Approved by hostel staff"
        ADMIN_OVERRIDE = "admin", "Platform admin override"

    hostel = models.ForeignKey("tenants.Hostel", on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hostel_reviews"
    )

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=120, blank=True, default="")
    body = models.TextField()
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    # Verification trail — snapshotted at verification time, so a later edit
    # or deletion of the source Resident/Student row can't retroactively
    # invalidate an already-published review.
    verification_method = models.CharField(
        max_length=12, choices=VerificationMethod.choices, blank=True, default=""
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    source_resident = models.ForeignKey(
        "residents.Resident", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    source_student = models.ForeignKey(
        "students.Student", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    resident_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    stay_start = models.DateField(null=True, blank=True)
    stay_end = models.DateField(null=True, blank=True)  # null = still resident

    flag_count = models.PositiveIntegerField(default=0)
    edit_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "author"], name="uniq_review_per_author_per_hostel"),
        ]
        indexes = [
            models.Index(fields=["hostel", "status", "-created_at"], name="review_hostel_status_idx"),
        ]

    def __str__(self):
        return f"{self.resident_name_snapshot or self.author_id} -> {self.hostel_id} ({self.rating}★)"


class ReviewResponse(TimeStampedModel):
    """One owner/manager reply per review, written from the hostel's own
    tenant dashboard."""

    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name="owner_response")
    body = models.TextField()
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    def __str__(self):
        return f"Response to {self.review_id}"


class ReviewFlag(TimeStampedModel):
    """A report against a review, driving auto-hide at a flag threshold and
    the platform-side moderation queue."""

    class Reason(models.TextChoices):
        SPAM = "spam", "Spam"
        FAKE = "fake", "Not a genuine resident"
        OFFENSIVE = "offensive", "Offensive content"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        DISMISSED = "dismissed", "Dismissed"
        ACTIONED = "actioned", "Actioned"

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="flags")
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reason = models.CharField(max_length=12, choices=Reason.choices)
    note = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Flag({self.review_id}, {self.reason})"
