from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Hostel, Plan, Subscription, Testimonial
from .validators import clean_workspace_username

class PlanSerializer(serializers.ModelSerializer):
    """Full plan record for authenticated admin/catalog use."""
    discounted_price = serializers.ReadOnlyField()
    discount_live = serializers.ReadOnlyField()

    class Meta:
        model = Plan
        fields = "__all__"


class PublicPlanSerializer(serializers.ModelSerializer):
    """Display-ready, unauthenticated subset for the marketing landing page."""
    discounted_price = serializers.ReadOnlyField()
    discount_live = serializers.ReadOnlyField()

    class Meta:
        model = Plan
        fields = [
            "id", "name", "description", "features", "period", "currency",
            "price_monthly", "discounted_price", "discount_percent",
            "discount_label", "discount_live", "cta_label", "cta_href",
            "is_featured", "sort_order", "max_students", "max_rooms",
        ]

class HostelSerializer(serializers.ModelSerializer):
    workspace_url = serializers.ReadOnlyField()

    class Meta:
        model = Hostel
        fields = ["id", "name", "code", "slug", "workspace_url", "status",
                  "phone", "address", "plan_name",
                  "subscription_active_until", "is_active", "settings", "created_at"]
        read_only_fields = ["id", "code", "slug", "workspace_url", "status", "created_at"]


class WorkspaceSerializer(serializers.ModelSerializer):
    """Full workspace record for members. The workspace username (slug) is
    permanent — writable fields are the display/branding/locale ones only."""

    workspace_url = serializers.ReadOnlyField()
    subdomain = serializers.ReadOnlyField()

    class Meta:
        model = Hostel
        fields = [
            "id", "name", "code", "slug", "subdomain", "workspace_url",
            "status", "is_active", "trial_ends_at",
            "phone", "address", "owner_name",
            "timezone", "currency", "language", "logo",
            "plan_name", "subscription_active_until", "settings",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "code", "slug", "subdomain", "workspace_url", "status",
            "is_active", "trial_ends_at", "plan_name",
            "subscription_active_until", "created_at", "updated_at",
        ]


class WorkspaceRegisterSerializer(serializers.Serializer):
    """Input for creating a new workspace (authenticated registration)."""

    hostel_name = serializers.CharField(max_length=120)
    workspace_username = serializers.CharField(
        required=False, allow_blank=True, max_length=63,
        help_text="Permanent workspace username; auto-generated from the "
                  "hostel name when omitted.",
    )
    phone = serializers.CharField(required=False, allow_blank=True, max_length=30)
    address = serializers.CharField(required=False, allow_blank=True, max_length=255)
    timezone = serializers.CharField(required=False, allow_blank=True, max_length=64)
    currency = serializers.CharField(required=False, allow_blank=True, max_length=8)
    language = serializers.CharField(required=False, allow_blank=True, max_length=16)

    def validate_workspace_username(self, value):
        if not value:
            return ""
        try:
            return clean_workspace_username(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"


class PublicTestimonialSerializer(serializers.ModelSerializer):
    """Display-ready, unauthenticated subset for the landing testimonials."""
    class Meta:
        model = Testimonial
        fields = ["id", "author_name", "author_role", "rating", "quote", "created_at"]


class TestimonialSubmitSerializer(serializers.ModelSerializer):
    """Public review submission. Everything else (approval/featuring) is admin-only."""
    class Meta:
        model = Testimonial
        fields = ["author_name", "author_role", "rating", "quote"]
        extra_kwargs = {
            "author_role": {"required": False},
        }

    def validate_quote(self, value):
        value = (value or "").strip()
        if len(value) < 10:
            raise serializers.ValidationError("Please share a little more (at least 10 characters).")
        return value
