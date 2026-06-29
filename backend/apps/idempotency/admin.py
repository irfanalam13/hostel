from django.contrib import admin

from .models import IdempotencyRecord


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ("key", "method", "path", "status_code", "user", "created_at")
    list_filter = ("method", "status_code")
    search_fields = ("key", "path")
    readonly_fields = [f.name for f in IdempotencyRecord._meta.fields]
