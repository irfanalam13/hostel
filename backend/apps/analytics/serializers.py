from rest_framework import serializers

from .models import EventType


class AnalyticsEventInSerializer(serializers.Serializer):
    """One incoming telemetry event."""

    event_type = serializers.ChoiceField(choices=EventType.choices)
    name = serializers.CharField(required=False, allow_blank=True, default="", max_length=200)
    value = serializers.FloatField(required=False, default=0)
    occurred_at = serializers.DateTimeField(required=False, allow_null=True)
    meta = serializers.DictField(required=False, default=dict)


class CollectSerializer(serializers.Serializer):
    """A batch of events plus client-reported versions."""

    events = AnalyticsEventInSerializer(many=True, allow_empty=False, max_length=200)
    app_version = serializers.CharField(required=False, allow_blank=True, default="", max_length=40)
    sw_version = serializers.CharField(required=False, allow_blank=True, default="", max_length=40)
