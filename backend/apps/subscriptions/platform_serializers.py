"""Serializers for the Super-Admin platform API.

Distinct from the tenant-facing serializers in ``apps.tenants``: these expose
the full editable surface (pricing, internal notes, lifecycle flags, feature
and limit wiring) and are only ever reachable behind ``IsPlatformAdmin``.
"""
from rest_framework import serializers

from apps.tenants.models import Plan

from .models import (
    Feature,
    FeatureCategory,
    FeatureDependency,
    FeatureOverride,
    LimitDefinition,
    LimitOverride,
    SubscriptionEvent,
)


class FeatureCategorySerializer(serializers.ModelSerializer):
    feature_count = serializers.IntegerField(source="features.count", read_only=True)

    class Meta:
        model = FeatureCategory
        fields = [
            "id", "key", "name", "description", "icon", "color",
            "sort_order", "is_active", "feature_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class FeatureSerializer(serializers.ModelSerializer):
    category_key = serializers.SlugField(source="category.key", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    requires = serializers.SerializerMethodField()

    class Meta:
        model = Feature
        fields = [
            "id", "key", "name", "display_name", "description",
            "category", "category_key", "category_name",
            "icon", "sort_order", "default_enabled", "release_stage",
            "is_beta", "is_enterprise_only", "is_active", "requires",
            "created_by", "updated_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "updated_by", "created_at", "updated_at"]

    def get_requires(self, obj) -> list:
        return [d.requires.key for d in obj.dependency_links.all()]


class FeatureDependencySerializer(serializers.ModelSerializer):
    feature_key = serializers.SlugField(source="feature.key", read_only=True)
    requires_key = serializers.SlugField(source="requires.key", read_only=True)

    class Meta:
        model = FeatureDependency
        fields = ["id", "feature", "feature_key", "requires", "requires_key", "note"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        feature = attrs.get("feature")
        requires = attrs.get("requires")
        if feature and requires and feature == requires:
            raise serializers.ValidationError("A feature cannot depend on itself.")
        return attrs


class LimitDefinitionSerializer(serializers.ModelSerializer):
    category_key = serializers.SlugField(source="category.key", read_only=True, default=None)

    class Meta:
        model = LimitDefinition
        fields = [
            "id", "key", "name", "description", "unit", "category", "category_key",
            "default_value", "allow_unlimited", "sort_order", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PlatformPlanSerializer(serializers.ModelSerializer):
    """Full plan surface for the Super Admin (slug is auto-derived).

    Named distinctly from ``apps.tenants.PlanSerializer`` to avoid an OpenAPI
    component-name collision.
    """

    feature_count = serializers.SerializerMethodField()
    discounted_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Plan
        fields = [
            "id", "name", "slug", "description", "notes", "version",
            "price_monthly", "price_yearly", "price_lifetime", "discounted_price",
            "currency", "period", "billing_interval", "trial_days",
            "grace_period_days", "tax_percent",
            "max_students", "max_rooms",
            "badge", "theme_color", "visibility", "is_recommended",
            "is_active", "is_archived", "is_featured", "is_public", "sort_order",
            "features", "cta_label", "cta_href",
            "discount_active", "discount_percent", "discount_label", "discount_until",
            "feature_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "discounted_price", "created_at", "updated_at"]

    def get_feature_count(self, obj) -> int:
        return obj.plan_features.filter(is_enabled=True).count()


class FeatureOverrideSerializer(serializers.ModelSerializer):
    feature_key = serializers.SlugField(source="feature.key", read_only=True)
    feature_name = serializers.CharField(source="feature.label", read_only=True)
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)
    is_live = serializers.BooleanField(read_only=True)

    class Meta:
        model = FeatureOverride
        fields = [
            "id", "hostel", "hostel_name", "feature", "feature_key", "feature_name",
            "is_enabled", "reason", "expires_at", "is_live",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class LimitOverrideSerializer(serializers.ModelSerializer):
    limit_key = serializers.SlugField(source="limit.key", read_only=True)
    limit_name = serializers.CharField(source="limit.name", read_only=True)
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)
    is_live = serializers.BooleanField(read_only=True)

    class Meta:
        model = LimitOverride
        fields = [
            "id", "hostel", "hostel_name", "limit", "limit_key", "limit_name",
            "value", "is_unlimited", "reason", "expires_at", "is_live",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class SubscriptionEventSerializer(serializers.ModelSerializer):
    from_plan_name = serializers.CharField(source="from_plan.name", read_only=True, default=None)
    to_plan_name = serializers.CharField(source="to_plan.name", read_only=True, default=None)
    actor_name = serializers.CharField(source="actor.username", read_only=True, default=None)

    class Meta:
        model = SubscriptionEvent
        fields = [
            "id", "hostel", "from_plan", "from_plan_name", "to_plan", "to_plan_name",
            "kind", "status_after", "mrr_amount", "reason", "actor", "actor_name",
            "created_at",
        ]
        read_only_fields = fields
