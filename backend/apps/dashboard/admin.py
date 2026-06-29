from django.contrib import admin

from .models import UserPresence


@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    list_display = ("user", "hostel", "is_installed", "sw_version", "app_version", "last_seen")
    list_filter = ("is_installed", "hostel")
    search_fields = ("user__username", "user__email", "sw_version")
    readonly_fields = ("last_seen",)
    date_hierarchy = "last_seen"
