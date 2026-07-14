from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id", "role", "content", "tool_calls", "provider", "model",
            "tokens_prompt", "tokens_completion", "latency_ms", "error", "created_at",
        ]


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = [
            "id", "title", "agent", "provider", "model", "message_count",
            "last_message_at", "is_archived", "created_at",
        ]


class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ["messages"]
