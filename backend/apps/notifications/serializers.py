from rest_framework import serializers

from .models import (
    AudienceType,
    Notification,
    NotificationCategory,
    NotificationPriority,
    NotificationRecipient,
)


# --------------------------------------------------------------------------- #
# Push subscription (matches the frontend src/shared/pwa/push.ts contract)
# --------------------------------------------------------------------------- #
class PushSubscribeSerializer(serializers.Serializer):
    subscription = serializers.DictField()
    user_agent = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_subscription(self, value):
        endpoint = value.get("endpoint")
        keys = value.get("keys") or {}
        if not endpoint:
            raise serializers.ValidationError("subscription.endpoint is required")
        if not keys.get("p256dh") or not keys.get("auth"):
            raise serializers.ValidationError("subscription.keys.p256dh and .auth are required")
        return value


class PushUnsubscribeSerializer(serializers.Serializer):
    endpoint = serializers.CharField()


# --------------------------------------------------------------------------- #
# Inbox (a recipient's view of a notification — includes read state)
# --------------------------------------------------------------------------- #
class InboxNotificationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="notification.id", read_only=True)
    recipient_id = serializers.UUIDField(source="id", read_only=True)
    category = serializers.CharField(source="notification.category", read_only=True)
    priority = serializers.CharField(source="notification.priority", read_only=True)
    title = serializers.CharField(source="notification.title", read_only=True)
    body = serializers.CharField(source="notification.body", read_only=True)
    url = serializers.CharField(source="notification.url", read_only=True)
    data = serializers.JSONField(source="notification.data", read_only=True)
    created_at = serializers.DateTimeField(source="notification.created_at", read_only=True)

    class Meta:
        model = NotificationRecipient
        fields = [
            "id",
            "recipient_id",
            "category",
            "priority",
            "title",
            "body",
            "url",
            "data",
            "is_read",
            "read_at",
            "delivered",
            "created_at",
        ]


# --------------------------------------------------------------------------- #
# Sending (staff) + sent history with delivery stats
# --------------------------------------------------------------------------- #
class NotificationCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=160)
    body = serializers.CharField(allow_blank=True, required=False, default="")
    category = serializers.ChoiceField(
        choices=NotificationCategory.choices, default=NotificationCategory.GENERAL
    )
    priority = serializers.ChoiceField(
        choices=NotificationPriority.choices, default=NotificationPriority.NORMAL
    )
    url = serializers.CharField(required=False, allow_blank=True, default="/dashboard")
    icon = serializers.CharField(required=False, allow_blank=True, default="")
    tag = serializers.CharField(required=False, allow_blank=True, default="")
    data = serializers.DictField(required=False, default=dict)
    audience = serializers.ChoiceField(choices=AudienceType.choices, default=AudienceType.ALL)
    target_roles = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    user_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs.get("audience") == AudienceType.ROLE and not attrs.get("target_roles"):
            raise serializers.ValidationError({"target_roles": "Required when audience is ROLE."})
        if attrs.get("audience") == AudienceType.USER and not attrs.get("user_ids"):
            raise serializers.ValidationError({"user_ids": "Required when audience is USER."})
        return attrs


class NotificationAdminSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "category",
            "priority",
            "title",
            "body",
            "url",
            "audience",
            "target_roles",
            "status",
            "scheduled_at",
            "sent_at",
            "recipients_count",
            "delivered_count",
            "failed_count",
            "read_count",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = fields
