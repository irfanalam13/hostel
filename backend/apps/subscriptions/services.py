"""Plan-configuration services for the Super-Admin platform API.

Pure functions the platform viewsets call to resolve, mutate, duplicate and
import/export plan configuration. Keeping this logic here (not in views) makes
it reusable (management commands, tests) and keeps the API layer thin.
"""
from django.db import transaction

from .models import (
    Feature,
    FeatureDependency,
    LimitDefinition,
    PlanFeature,
    PlanLimit,
    ReleaseStage,
)


class DependencyError(Exception):
    """Raised when a feature set violates declared feature dependencies."""

    def __init__(self, violations):
        self.violations = violations
        super().__init__("Feature dependency violation")


# --------------------------------------------------------------------------- #
# Effective plan resolution (plan-level, no hostel/overrides)
# --------------------------------------------------------------------------- #
def plan_feature_map(plan) -> dict:
    """``{feature_key: enabled}`` effective for a plan.

    A PlanFeature row is authoritative; otherwise fall back to the catalog
    default (only stable features default on — the early-access gate).

    Queries PlanFeature directly (not ``plan.plan_features``) so it stays
    correct when called right after a write on a prefetched plan instance.
    """
    rows = {
        pf["feature_id"]: pf["is_enabled"]
        for pf in PlanFeature.objects.filter(plan=plan).values("feature_id", "is_enabled")
    }
    out = {}
    for f in Feature.objects.filter(is_active=True):
        if f.id in rows:
            out[f.key] = bool(rows[f.id])
        else:
            out[f.key] = bool(f.default_enabled) and f.release_stage == ReleaseStage.STABLE
    return out


def plan_limit_map(plan) -> dict:
    """``{limit_key: value}`` effective for a plan (None == unlimited)."""
    rows = {
        pl["limit_id"]: (None if pl["is_unlimited"] else pl["value"])
        for pl in PlanLimit.objects.filter(plan=plan).values("limit_id", "value", "is_unlimited")
    }
    out = {}
    for ld in LimitDefinition.objects.filter(is_active=True):
        out[ld.key] = rows[ld.id] if ld.id in rows else ld.default_value
    return out


# --------------------------------------------------------------------------- #
# Dependency validation (Module 8)
# --------------------------------------------------------------------------- #
def dependency_violations(enabled_keys) -> list:
    """Enabled features whose required features aren't also enabled."""
    enabled = set(enabled_keys)
    violations = []
    deps = FeatureDependency.objects.select_related("feature", "requires")
    for dep in deps:
        if dep.feature.key in enabled and dep.requires.key not in enabled:
            violations.append(
                {
                    "feature": dep.feature.key,
                    "feature_name": dep.feature.label,
                    "requires": dep.requires.key,
                    "requires_name": dep.requires.label,
                }
            )
    return violations


# --------------------------------------------------------------------------- #
# Mutations
# --------------------------------------------------------------------------- #
@transaction.atomic
def set_plan_features(plan, mapping: dict, *, force: bool = False) -> dict:
    """Upsert a plan's feature toggles from ``{feature_key: bool}``.

    Validates feature dependencies against the resulting *full* enabled set
    unless ``force`` is set; raises :class:`DependencyError` on violation.
    """
    features = {f.key: f for f in Feature.objects.all()}
    # Build the resulting enabled set: current effective map overlaid by input.
    effective = plan_feature_map(plan)
    for key, val in mapping.items():
        if key in features:
            effective[key] = bool(val)

    enabled_keys = {k for k, v in effective.items() if v}
    if not force:
        violations = dependency_violations(enabled_keys)
        if violations:
            raise DependencyError(violations)

    for key, val in mapping.items():
        feature = features.get(key)
        if not feature:
            continue
        PlanFeature.objects.update_or_create(
            plan=plan, feature=feature, defaults={"is_enabled": bool(val)}
        )
    return plan_feature_map(plan)


@transaction.atomic
def set_plan_limits(plan, mapping: dict) -> dict:
    """Upsert a plan's limits from ``{limit_key: {value, is_unlimited}}``."""
    limits = {ld.key: ld for ld in LimitDefinition.objects.all()}
    for key, spec in mapping.items():
        ld = limits.get(key)
        if not ld:
            continue
        is_unlimited = bool(spec.get("is_unlimited", False))
        value = int(spec.get("value", 0) or 0)
        PlanLimit.objects.update_or_create(
            plan=plan,
            limit=ld,
            defaults={"is_unlimited": is_unlimited, "value": max(value, 0)},
        )
    return plan_limit_map(plan)


@transaction.atomic
def duplicate_plan(plan, *, new_name: str = "", created_by=None):
    """Deep-copy a plan and all its feature/limit rows. The copy starts
    inactive and unlisted so it can be edited before going live."""
    from apps.tenants.models import Plan, PlanVisibility

    clone = Plan.objects.get(pk=plan.pk)
    clone.pk = None
    clone.id = None
    clone.slug = None  # re-derived in save()
    clone.name = new_name or f"{plan.name} Copy"
    clone.is_active = False
    clone.is_archived = False
    clone.visibility = PlanVisibility.PRIVATE
    clone.is_featured = False
    clone.is_recommended = False
    clone.version = 1
    clone.save()

    PlanFeature.objects.bulk_create(
        [
            PlanFeature(plan=clone, feature_id=pf.feature_id, is_enabled=pf.is_enabled)
            for pf in plan.plan_features.all()
        ]
    )
    PlanLimit.objects.bulk_create(
        [
            PlanLimit(
                plan=clone,
                limit_id=pl.limit_id,
                value=pl.value,
                is_unlimited=pl.is_unlimited,
            )
            for pl in plan.plan_limits.all()
        ]
    )
    return clone


# --------------------------------------------------------------------------- #
# Import / export (Module 18)
# --------------------------------------------------------------------------- #
_EXPORT_FIELDS = [
    "name", "slug", "description", "notes", "price_monthly", "price_yearly",
    "price_lifetime", "currency", "period", "billing_interval", "trial_days",
    "grace_period_days", "tax_percent", "badge", "theme_color", "visibility",
    "is_recommended", "is_active", "is_archived", "is_featured", "is_public",
    "sort_order", "version",
]


def export_plans() -> list:
    """Serialize every plan + its feature/limit configuration to plain dicts."""
    from apps.tenants.models import Plan

    out = []
    for plan in Plan.objects.all().prefetch_related("plan_features", "plan_limits"):
        row = {f: getattr(plan, f) for f in _EXPORT_FIELDS}
        # Decimals -> str for JSON round-trip stability.
        for k, v in list(row.items()):
            if hasattr(v, "quantize"):
                row[k] = str(v)
        row["features"] = plan_feature_map(plan)
        row["limits"] = {
            ld_key: {"value": None if val is None else val, "is_unlimited": val is None}
            for ld_key, val in plan_limit_map(plan).items()
        }
        out.append(row)
    return out


@transaction.atomic
def import_plans(rows: list, *, created_by=None) -> dict:
    """Upsert plans (matched by slug, then name) with their features/limits.
    Returns counts of created/updated plans."""
    from apps.tenants.models import Plan

    created = updated = 0
    for row in rows or []:
        row = dict(row)
        features = row.pop("features", {}) or {}
        limits = row.pop("limits", {}) or {}
        slug = (row.get("slug") or "").strip()
        name = (row.get("name") or "").strip()

        plan = None
        if slug:
            plan = Plan.objects.filter(slug=slug).first()
        if plan is None and name:
            plan = Plan.objects.filter(name__iexact=name).first()

        fields = {k: v for k, v in row.items() if k in _EXPORT_FIELDS}
        if plan is None:
            plan = Plan(**fields)
            plan.save()
            created += 1
        else:
            for k, v in fields.items():
                if k == "slug":
                    continue  # never mutate an existing plan's slug
                setattr(plan, k, v)
            plan.save()
            updated += 1

        if features:
            set_plan_features(plan, features, force=True)
        if limits:
            set_plan_limits(plan, limits)

    return {"created": created, "updated": updated}
