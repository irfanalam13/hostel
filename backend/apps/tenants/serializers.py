from rest_framework import serializers
from .models import Hostel, Plan, Subscription

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = "__all__"

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
