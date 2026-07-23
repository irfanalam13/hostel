from django.contrib import admin

from .models import IPRule, SecurityEvent, SecuritySetting


@admin.register(SecuritySetting)
class SecuritySettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "active", "updated_at", "updated_by")
    list_filter = ("active",)
    search_fields = ("key", "note")

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(IPRule)
class IPRuleAdmin(admin.ModelAdmin):
    list_display = ("cidr", "action", "tenant", "active", "expires_at", "note")
    list_filter = ("action", "active")
    search_fields = ("cidr", "note")
    raw_id_fields = ("tenant",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    """Immutable audit trail — strictly read-only in the admin."""

    list_display = ("created_at", "event_type", "action", "ip", "method",
                    "path", "tenant", "threat_score")
    list_filter = ("event_type", "action")
    search_fields = ("ip", "path", "request_id", "user_agent")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
