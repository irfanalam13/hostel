from django.contrib import admin

from .models import (
    Announcement,
    FeatureFlag,
    FeatureFlagOverride,
    Incident,
    IncidentUpdate,
    MaintenanceWindow,
)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "audience", "is_active", "starts_at", "ends_at")
    list_filter = ("level", "audience", "is_active")
    search_fields = ("title", "body")


@admin.register(MaintenanceWindow)
class MaintenanceWindowAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "scheduled_start", "scheduled_end", "enforce_read_only")
    list_filter = ("status", "enforce_read_only")
    search_fields = ("title", "description")


class IncidentUpdateInline(admin.TabularInline):
    model = IncidentUpdate
    extra = 0


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("title", "severity", "status", "is_public", "started_at", "resolved_at")
    list_filter = ("severity", "status", "is_public")
    search_fields = ("title", "summary")
    inlines = [IncidentUpdateInline]


class FeatureFlagOverrideInline(admin.TabularInline):
    model = FeatureFlagOverride
    extra = 0
    fk_name = "flag"


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "is_active", "kill", "rollout_percentage")
    list_filter = ("is_active", "kill")
    search_fields = ("key", "name", "description")
    inlines = [FeatureFlagOverrideInline]


@admin.register(FeatureFlagOverride)
class FeatureFlagOverrideAdmin(admin.ModelAdmin):
    list_display = ("flag", "hostel_id", "user", "enabled", "expires_at")
    list_filter = ("enabled",)
