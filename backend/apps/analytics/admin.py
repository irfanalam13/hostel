from django.contrib import admin

from .models import AnalyticsEvent


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_type", "name", "value", "device_type", "browser",
        "user", "hostel", "created_at",
    )
    list_filter = ("event_type", "device_type", "browser", "hostel")
    search_fields = ("name", "user__username")
    readonly_fields = [f.name for f in AnalyticsEvent._meta.fields]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False  # events are ingested via the API, never hand-created
