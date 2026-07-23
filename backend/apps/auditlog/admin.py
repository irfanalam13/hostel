from django.contrib import admin

from .models import AuditChainState, AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """Read-only admin — audit events are append-only and immutable."""

    list_display = ("created_at", "sequence", "action", "result", "actor",
                    "entity_type", "entity_id", "message")
    list_filter = ("action", "result", "created_at")
    search_fields = ("message", "reason", "entity_id", "entity_type", "request_id")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditChainState)
class AuditChainStateAdmin(admin.ModelAdmin):
    list_display = ("id", "sequence", "last_hash", "checkpoint_sequence", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
