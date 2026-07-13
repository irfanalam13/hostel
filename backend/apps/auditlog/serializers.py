from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    """Read-only projection of an immutable audit event.

    Exposes the hash-chain columns so a client can independently re-verify
    tamper-evidence, plus a friendly actor label.
    """

    actor_label = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = (
            "id", "sequence", "created_at",
            "action", "result", "status_code", "duration_ms",
            "actor", "actor_label", "hostel_id", "branch_id",
            "entity_type", "entity_id",
            "message", "reason", "changes", "meta",
            "ip_address", "user_agent", "request_id",
            "prev_hash", "content_hash",
        )
        read_only_fields = fields

    def get_actor_label(self, obj):
        actor = obj.actor
        if actor is None:
            return None
        name = (getattr(actor, "get_full_name", lambda: "")() or "").strip()
        return name or getattr(actor, "email", None) or getattr(actor, "username", None) or str(actor.pk)
