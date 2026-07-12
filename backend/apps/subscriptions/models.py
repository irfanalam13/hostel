"""Enterprise subscription & plan management — core registry.

The whole subscription system is database-driven: features, categories, limit
definitions and their per-plan wiring all live here so the Super Admin can
create/edit/toggle everything without a code change (Modules 1, 4 & 21).

Design notes
------------
* Plans themselves live on ``tenants.Plan`` (extended in place so the public
  landing page keeps working). This app owns the *catalog* (features, limits)
  and the *junctions* (which plan enables which feature / sets which limit).
* Everything inherits ``TimeStampedModel`` → UUID PK + created/updated stamps.
* Feature/limit ``key`` fields are the stable machine identifiers the runtime
  entitlement engine (Phase 2) resolves against. Display fields are free to
  change; keys are not (enforced by uniqueness + admin conventions).
"""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


# --------------------------------------------------------------------------- #
# Shared enums
# --------------------------------------------------------------------------- #
class ReleaseStage(models.TextChoices):
    """Maturity / rollout gate for a feature (Module 14 — early access)."""

    STABLE = "stable", "Stable"
    BETA = "beta", "Beta"
    EXPERIMENTAL = "experimental", "Experimental"
    INTERNAL = "internal", "Internal"
    INVITE_ONLY = "invite_only", "Invite only"


# --------------------------------------------------------------------------- #
# Module 1 — Feature categories
# --------------------------------------------------------------------------- #
class FeatureCategory(TimeStampedModel):
    """A grouping bucket for features (General, Finance, AI, …)."""

    key = models.SlugField(max_length=60, unique=True, db_index=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=255, blank=True, default="")
    icon = models.CharField(max_length=60, blank=True, default="")
    color = models.CharField(max_length=20, blank=True, default="")
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "feature categories"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


# --------------------------------------------------------------------------- #
# Module 1 — Feature master registry
# --------------------------------------------------------------------------- #
class Feature(TimeStampedModel):
    """A single capability of the SaaS, defined exactly once.

    The ``key`` is the identifier the runtime checks (e.g. ``ai_reports``);
    it never changes. Everything else is Super-Admin editable.
    """

    key = models.SlugField(max_length=80, unique=True, db_index=True)
    name = models.CharField(max_length=120)
    display_name = models.CharField(max_length=120, blank=True, default="")
    description = models.TextField(blank=True, default="")

    category = models.ForeignKey(
        FeatureCategory,
        on_delete=models.PROTECT,
        related_name="features",
    )

    icon = models.CharField(max_length=60, blank=True, default="")
    sort_order = models.IntegerField(default=0)

    # Whether a brand-new plan starts with this feature enabled.
    default_enabled = models.BooleanField(default=False)

    release_stage = models.CharField(
        max_length=20,
        choices=ReleaseStage.choices,
        default=ReleaseStage.STABLE,
        db_index=True,
    )
    is_beta = models.BooleanField(default=False)
    is_enterprise_only = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    # Self-referential dependency graph (Module 8). ``requires`` = features
    # that must also be enabled for this one to be valid.
    dependencies = models.ManyToManyField(
        "self",
        through="FeatureDependency",
        symmetrical=False,
        related_name="dependents",
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["category__sort_order", "sort_order", "name"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["is_active", "release_stage"]),
        ]

    def __str__(self):
        return self.display_name or self.name

    @property
    def label(self) -> str:
        return self.display_name or self.name


class FeatureDependency(TimeStampedModel):
    """``feature`` requires ``requires`` to also be enabled (Module 8)."""

    feature = models.ForeignKey(
        Feature, on_delete=models.CASCADE, related_name="dependency_links"
    )
    requires = models.ForeignKey(
        Feature, on_delete=models.CASCADE, related_name="required_by_links"
    )
    note = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        verbose_name_plural = "feature dependencies"
        constraints = [
            models.UniqueConstraint(
                fields=["feature", "requires"], name="uniq_feature_dependency"
            ),
            models.CheckConstraint(
                condition=~models.Q(feature=models.F("requires")),
                name="feature_dependency_not_self",
            ),
        ]

    def __str__(self):
        return f"{self.feature_id} → requires {self.requires_id}"


# --------------------------------------------------------------------------- #
# Module 4 — Limit definitions (the catalog of quantifiable quotas)
# --------------------------------------------------------------------------- #
class LimitDefinition(TimeStampedModel):
    """A quantifiable quota key (max_students, max_storage_mb, …).

    Plans set a value per definition via ``PlanLimit``. ``allow_unlimited``
    lets a plan mark the quota as unbounded without a magic sentinel value.
    """

    key = models.SlugField(max_length=80, unique=True, db_index=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True, default="")
    unit = models.CharField(
        max_length=30, blank=True, default="", help_text="e.g. 'students', 'MB', 'req/mo'."
    )

    category = models.ForeignKey(
        FeatureCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="limit_definitions",
    )

    # Value a plan gets when it has no explicit PlanLimit row.
    default_value = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    allow_unlimited = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


# --------------------------------------------------------------------------- #
# Module 3 — Plan ↔ Feature junction
# --------------------------------------------------------------------------- #
class PlanFeature(TimeStampedModel):
    """Whether a given plan enables a given feature."""

    plan = models.ForeignKey(
        "tenants.Plan", on_delete=models.CASCADE, related_name="plan_features"
    )
    feature = models.ForeignKey(
        Feature, on_delete=models.CASCADE, related_name="plan_features"
    )
    is_enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "feature"], name="uniq_plan_feature"
            ),
        ]
        indexes = [
            models.Index(fields=["plan", "is_enabled"]),
        ]

    def __str__(self):
        state = "on" if self.is_enabled else "off"
        return f"{self.plan_id}:{self.feature_id} ({state})"


# --------------------------------------------------------------------------- #
# Module 4 — Plan ↔ Limit junction
# --------------------------------------------------------------------------- #
class PlanLimit(TimeStampedModel):
    """The numeric quota a plan grants for a limit definition."""

    plan = models.ForeignKey(
        "tenants.Plan", on_delete=models.CASCADE, related_name="plan_limits"
    )
    limit = models.ForeignKey(
        LimitDefinition, on_delete=models.CASCADE, related_name="plan_limits"
    )
    # ``value`` is ignored when ``is_unlimited`` is True.
    value = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_unlimited = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "limit"], name="uniq_plan_limit"
            ),
        ]
        indexes = [
            models.Index(fields=["plan"]),
        ]

    def __str__(self):
        val = "∞" if self.is_unlimited else self.value
        return f"{self.plan_id}:{self.limit_id} = {val}"

    @property
    def effective_value(self):
        """Resolved quota: ``None`` means unlimited."""
        return None if self.is_unlimited else self.value


# --------------------------------------------------------------------------- #
# Module 13 & 14 — Per-hostel overrides / early access
# --------------------------------------------------------------------------- #
class OverrideBase(TimeStampedModel):
    """Shared fields for hostel-scoped entitlement overrides.

    An override wins over the plan's value for one specific hostel. Use it to
    grant/revoke a feature (incl. enrolling a hostel in a beta/early-access
    feature — Module 14) or to bump a limit, temporarily or permanently, for a
    single tenant without touching the plan (Module 13).
    """

    hostel = models.ForeignKey(
        "tenants.Hostel", on_delete=models.CASCADE, related_name="%(class)ss"
    )
    reason = models.CharField(max_length=255, blank=True, default="")
    # ``None`` = permanent. Otherwise the override stops applying after this.
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        abstract = True

    @property
    def is_live(self) -> bool:
        return self.expires_at is None or self.expires_at > timezone.now()


class FeatureOverride(OverrideBase):
    """Grant (``is_enabled=True``) or revoke (``False``) a feature for one hostel."""

    feature = models.ForeignKey(
        Feature, on_delete=models.CASCADE, related_name="overrides"
    )
    is_enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "feature"], name="uniq_feature_override"
            ),
        ]
        indexes = [models.Index(fields=["hostel", "feature"])]

    def __str__(self):
        verb = "grant" if self.is_enabled else "revoke"
        return f"{self.hostel_id}: {verb} {self.feature_id}"


class LimitOverride(OverrideBase):
    """Override a limit's value (or mark it unlimited) for one hostel."""

    limit = models.ForeignKey(
        LimitDefinition, on_delete=models.CASCADE, related_name="overrides"
    )
    value = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_unlimited = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "limit"], name="uniq_limit_override"
            ),
        ]
        indexes = [models.Index(fields=["hostel", "limit"])]

    def __str__(self):
        val = "∞" if self.is_unlimited else self.value
        return f"{self.hostel_id}: {self.limit_id} = {val}"

    @property
    def effective_value(self):
        return None if self.is_unlimited else self.value


# --------------------------------------------------------------------------- #
# Module 9 — Hostel subscription lifecycle history
# --------------------------------------------------------------------------- #
class SubscriptionEvent(TimeStampedModel):
    """An immutable record of a change to a hostel's subscription.

    Powers the upgrade/downgrade/renewal history and feeds analytics. Written
    by ``lifecycle.assign_plan`` on every plan change.
    """

    class Kind(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        UPGRADED = "upgraded", "Upgraded"
        DOWNGRADED = "downgraded", "Downgraded"
        RENEWED = "renewed", "Renewed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        REACTIVATED = "reactivated", "Reactivated"

    hostel = models.ForeignKey(
        "tenants.Hostel", on_delete=models.CASCADE, related_name="subscription_events"
    )
    from_plan = models.ForeignKey(
        "tenants.Plan", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    to_plan = models.ForeignKey(
        "tenants.Plan", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, db_index=True)
    status_after = models.CharField(max_length=20, blank=True, default="")
    # Monthly-equivalent recurring amount after the change (for MRR history).
    mrr_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reason = models.CharField(max_length=255, blank=True, default="")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["hostel", "-created_at"])]

    def __str__(self):
        return f"{self.hostel_id}: {self.kind} → {self.to_plan_id}"
