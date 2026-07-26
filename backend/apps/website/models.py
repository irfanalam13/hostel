"""Website Builder (CMS) models — one public website per workspace.

Editing always happens on the *draft* (the ``Website`` row + its
``WebsiteSection`` rows). Publishing snapshots the entire draft into an
immutable ``WebsiteVersion`` and stamps it as the live version; the public
endpoint serves ONLY the published snapshot, so half-edited drafts can never
leak. Rollback restores any version's snapshot into the draft (and republish
makes it live again).

Everything is FK'd to the tenant — assets, sections, versions, inquiries —
so isolation follows the same rules as every other scoped model.
"""
from django.conf import settings
from django.db import models

from apps.common.models import HostelScopedModel, TimeStampedModel
from .sections import (
    DEFAULT_BRANDING,
    DEFAULT_FOOTER,
    DEFAULT_NAVIGATION,
    DEFAULT_SEO,
    DEFAULT_SOCIAL,
    DEFAULT_THEME,
    SECTION_TYPES,
)


class Website(TimeStampedModel):
    """The draft (working copy) of a workspace's public website."""

    hostel = models.OneToOneField(
        "tenants.Hostel", on_delete=models.CASCADE, related_name="website"
    )

    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    # The live snapshot served to the public (copy of the current version's
    # snapshot, denormalized for a single-row public read).
    published_snapshot = models.JSONField(default=dict, blank=True)
    published_version = models.IntegerField(default=0)

    theme = models.JSONField(default=dict, blank=True)
    seo = models.JSONField(default=dict, blank=True)
    branding = models.JSONField(default=dict, blank=True)
    navigation = models.JSONField(default=dict, blank=True)
    footer = models.JSONField(default=dict, blank=True)
    social = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Website({self.hostel_id})"

    # Effective settings = defaults overlaid with the stored values, so new
    # keys added to the defaults appear without a data migration.
    def effective_theme(self):
        return {**DEFAULT_THEME, **(self.theme or {})}

    def effective_seo(self):
        return {**DEFAULT_SEO, **(self.seo or {})}

    def effective_branding(self):
        return {**DEFAULT_BRANDING, **(self.branding or {})}

    def effective_navigation(self):
        return {**DEFAULT_NAVIGATION, **(self.navigation or {})}

    def effective_footer(self):
        return {**DEFAULT_FOOTER, **(self.footer or {})}

    def effective_social(self):
        return {**DEFAULT_SOCIAL, **(self.social or {})}


class WebsiteSection(TimeStampedModel):
    """One typed block on the draft website, ordered top to bottom."""

    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name="sections")
    type = models.CharField(max_length=32, choices=[(t, cfg["label"]) for t, cfg in SECTION_TYPES.items()])
    order = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    content = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order", "created_at"]
        indexes = [models.Index(fields=["website", "order"], name="website_section_order_idx")]

    def __str__(self):
        return f"{self.type}#{self.order}"


class WebsiteVersion(TimeStampedModel):
    """Immutable snapshot created on every publish; the rollback unit."""

    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name="versions")
    number = models.IntegerField()
    snapshot = models.JSONField(default=dict)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    note = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["-number"]
        constraints = [
            models.UniqueConstraint(fields=["website", "number"], name="uniq_website_version"),
        ]

    def __str__(self):
        return f"v{self.number}"


class WebsiteInquiry(HostelScopedModel):
    """A public visitor's inquiry, stored tenant-scoped for the admin inbox."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        READ = "read", "Read"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    room_interest = models.CharField(max_length=120, blank=True, default="")
    message = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "website inquiries"

    def __str__(self):
        return f"{self.name} ({self.status})"


def _media_upload_to(instance, filename):
    # Tenant-prefixed path: assets can never collide or be enumerated across
    # workspaces by path guessing alone.
    return f"website/{instance.hostel_id}/{filename}"


class WebsiteMedia(HostelScopedModel):
    """Uploaded website asset (image or PDF), validated at the API layer."""

    class Kind(models.TextChoices):
        IMAGE = "image", "Image"
        DOCUMENT = "document", "Document"

    file = models.FileField(upload_to=_media_upload_to)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.IMAGE)
    alt_text = models.CharField(max_length=200, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "website media"

    def __str__(self):
        return self.file.name
