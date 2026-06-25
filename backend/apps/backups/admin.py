from django.contrib import admin

from .models import BackupSnapshot, DRState, RestoreRun


@admin.register(BackupSnapshot)
class BackupSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "hostel", "period", "schema_version", "size_bytes", "is_valid", "created_at")
    list_filter = ("period", "is_valid", "schema_version")
    search_fields = ("hostel__code", "hostel__name", "checksum")
    readonly_fields = ("checksum", "size_bytes", "schema_version", "validated_at")
    date_hierarchy = "created_at"


@admin.register(RestoreRun)
class RestoreRunAdmin(admin.ModelAdmin):
    list_display = ("id", "hostel", "status", "dry_run", "force", "performed_by", "created_at")
    list_filter = ("status", "dry_run", "force")
    search_fields = ("hostel__code",)
    readonly_fields = ("stats", "error", "started_at", "finished_at", "pre_restore_snapshot")
    date_hierarchy = "created_at"


@admin.register(DRState)
class DRStateAdmin(admin.ModelAdmin):
    list_display = ("singleton_id", "mode", "reason", "changed_by", "changed_at")
