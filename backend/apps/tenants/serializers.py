from rest_framework import serializers
from .models import Hostel, Plan, Subscription, Testimonial

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
    class Meta:
        model = Hostel
        fields = ["id", "name", "code", "phone", "address", "plan_name",
                  "subscription_active_until", "is_active", "settings", "created_at"]
        read_only_fields = ["id", "code", "created_at"]
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
