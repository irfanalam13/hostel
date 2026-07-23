from rest_framework import serializers

from .models import (
    Announcement,
    FeatureFlag,
    FeatureFlagOverride,
    Incident,
    IncidentUpdate,
    MaintenanceWindow,
)


class AnnouncementSerializer(serializers.ModelSerializer):
    live = serializers.BooleanField(read_only=True)

    class Meta:
        model = Announcement
        fields = (
            "id", "title", "body", "level", "audience", "is_active",
            "dismissible", "starts_at", "ends_at", "live",
            "created_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "live", "created_by", "created_at", "updated_at")


class MaintenanceWindowSerializer(serializers.ModelSerializer):
    is_current = serializers.BooleanField(read_only=True)

    class Meta:
        model = MaintenanceWindow
        fields = (
            "id", "title", "description", "status", "scheduled_start",
            "scheduled_end", "enforce_read_only", "components", "is_current",
            "created_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "is_current", "created_by", "created_at", "updated_at")

    def validate(self, attrs):
        start = attrs.get("scheduled_start") or getattr(self.instance, "scheduled_start", None)
        end = attrs.get("scheduled_end") or getattr(self.instance, "scheduled_end", None)
        if start and end and end <= start:
            raise serializers.ValidationError("scheduled_end must be after scheduled_start.")
        return attrs


class IncidentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentUpdate
        fields = ("id", "incident", "status", "message", "created_by", "created_at")
        read_only_fields = ("id", "incident", "created_by", "created_at")


class IncidentSerializer(serializers.ModelSerializer):
    updates = IncidentUpdateSerializer(many=True, read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Incident
        fields = (
            "id", "title", "summary", "severity", "status", "components",
            "is_public", "started_at", "resolved_at", "is_open", "updates",
            "created_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "is_open", "updates", "created_by",
                            "created_at", "updated_at", "resolved_at")


class FeatureFlagOverrideSerializer(serializers.ModelSerializer):
    is_live = serializers.BooleanField(read_only=True)
    schedule_state = serializers.CharField(read_only=True)
    flag_key = serializers.CharField(source="flag.key", read_only=True)
    hostel_label = serializers.SerializerMethodField()
    user_label = serializers.SerializerMethodField()

    class Meta:
        model = FeatureFlagOverride
        fields = (
            "id", "flag", "flag_key", "hostel_id", "hostel_label",
            "user", "user_label", "enabled", "reason",
            "starts_at", "expires_at", "is_active", "is_live", "schedule_state",
            "created_by", "created_at",
        )
        read_only_fields = (
            "id", "flag_key", "hostel_label", "user_label", "is_live",
            "schedule_state", "created_by", "created_at",
        )

    def get_hostel_label(self, obj):
        if not obj.hostel_id:
            return None
        from apps.tenants.models import Hostel

        hostel = Hostel.objects.filter(id=obj.hostel_id).only("name", "code").first()
        return f"{hostel.name} ({hostel.code})" if hostel else str(obj.hostel_id)

    def get_user_label(self, obj):
        user = obj.user
        if user is None:
            return None
        name = (getattr(user, "get_full_name", lambda: "")() or "").strip()
        return name or getattr(user, "email", None) or getattr(user, "username", None) or str(user.pk)

    def validate(self, attrs):
        hostel_id = attrs.get("hostel_id") or getattr(self.instance, "hostel_id", None)
        user = attrs.get("user") or getattr(self.instance, "user", None)
        if not hostel_id and not user:
            raise serializers.ValidationError("An override must target a hostel or a user.")
        starts = attrs.get("starts_at") or getattr(self.instance, "starts_at", None)
        expires = attrs.get("expires_at") or getattr(self.instance, "expires_at", None)
        if starts and expires and expires <= starts:
            raise serializers.ValidationError("expires_at must be after starts_at.")
        return attrs


class FeatureFlagSerializer(serializers.ModelSerializer):
    overrides = FeatureFlagOverrideSerializer(many=True, read_only=True)

    class Meta:
        model = FeatureFlag
        fields = (
            "id", "key", "name", "description", "is_active", "kill",
            "rollout_percentage", "allowed_hostels", "blocked_hostels",
            "allowed_roles", "overrides", "created_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "overrides", "created_by", "created_at", "updated_at")

    def validate_rollout_percentage(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("rollout_percentage must be between 0 and 100.")
        return value
