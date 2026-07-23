"""Serializers for the Super-Admin security ops API."""
import ipaddress

from rest_framework import serializers

from .models import IPRule, SecurityEvent, SecuritySetting


class SecurityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityEvent
        fields = [
            "id", "created_at", "event_type", "action", "ip", "method", "path",
            "user_agent", "request_id", "country", "asn", "threat_score",
            "tenant_id", "user_id", "detail",
        ]
        read_only_fields = fields


class IPRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = IPRule
        fields = [
            "id", "cidr", "action", "tenant", "active", "expires_at", "note",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_cidr(self, value):
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError as exc:
            raise serializers.ValidationError(f"Invalid IP/CIDR: {value!r}") from exc
        return value


class SecuritySettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecuritySetting
        fields = ["id", "key", "value", "active", "note", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class KillSwitchSerializer(serializers.Serializer):
    """Emergency toggles. Each maps to a SecuritySetting override that hot-
    reloads across all containers (no redeploy)."""

    # rate_limiter/auth/waf/bots disable a security subsystem (config, hot
    # reload); maintenance/emergency delegate to the existing DR mode
    # (apps.backups) rather than a parallel lock.
    TARGETS = ("rate_limiter", "auth", "waf", "bots", "maintenance", "emergency")

    target = serializers.ChoiceField(choices=TARGETS)
    # True = engage the kill switch (disable/lock), False = restore.
    engage = serializers.BooleanField(default=True)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
