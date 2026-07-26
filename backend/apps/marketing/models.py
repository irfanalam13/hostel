"""
Marketing / public-content models.

Everything the public landing pages render is editable here (and via the Django
admin), so copy changes don't need a redeploy:

  - Faq            the FAQ accordion
  - LegalDocument  Privacy / Terms / Security pages (slug-addressed)
  - SitePage       generic content pages (e.g. About), rendered from JSON blocks
  - Lead           "contact sales / request a demo" form submissions
"""
from django.db import models
from apps.common.models import TimeStampedModel


class Faq(TimeStampedModel):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    category = models.CharField(max_length=60, blank=True, default="")
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.question


class LegalDocument(TimeStampedModel):
    """A long-form legal/trust page addressed by slug (privacy/terms/security)."""
    slug = models.SlugField(max_length=40, unique=True)
    eyebrow = models.CharField(max_length=60, blank=True, default="Legal")
    title = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True, default="")
    last_updated = models.CharField(max_length=60, blank=True, default="")
    # List of {heading, body: [str], bullets?: [str]} — matches the frontend
    # LegalDocument component's section shape exactly.
    sections = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["slug"]

    def __str__(self):
        return self.title


class SitePage(TimeStampedModel):
    """
    Generic content page (e.g. About) addressed by slug. `body` is a list of
    blocks the frontend knows how to render:

      {"type": "prose", "heading": str, "paragraphs": [str]}
      {"type": "cards", "items": [{"icon": str, "title": str, "description": str}]}
    """
    slug = models.SlugField(max_length=40, unique=True)
    eyebrow = models.CharField(max_length=60, blank=True, default="")
    title = models.CharField(max_length=160)
    description = models.CharField(max_length=400, blank=True, default="")
    body = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["slug"]

    def __str__(self):
        return self.title


class Lead(TimeStampedModel):
    """A sales/demo enquiry submitted from the public Contact section."""

    class Kind(models.TextChoices):
        DEMO = "demo", "Demo request"
        SALES = "sales", "Contact sales"
        GENERAL = "general", "General enquiry"

    name = models.CharField(max_length=120)
    email = models.EmailField()
    organization = models.CharField(max_length=160, blank=True, default="")
    message = models.TextField()
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.DEMO)
    is_handled = models.BooleanField(default=False)
    source = models.CharField(max_length=40, blank=True, default="landing")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}> ({self.kind})"
