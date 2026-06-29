from django.contrib import admin, messages

from .models import (
    Notification,
    NotificationDelivery,
    NotificationRecipient,
    NotificationStatus,
    PushSubscription,
)
from .services import dispatch


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "hostel", "is_active", "failure_count", "last_used_at", "created_at")
    list_filter = ("is_active", "hostel")
    search_fields = ("user__username", "user__email", "endpoint")
    readonly_fields = ("endpoint", "p256dh", "auth", "user_agent", "last_used_at", "failure_count")
    date_hierarchy = "created_at"


class NotificationRecipientInline(admin.TabularInline):
    model = NotificationRecipient
    extra = 0
    fields = ("user", "delivered", "is_read", "read_at")
    readonly_fields = fields
    can_delete = False
    show_change_link = True


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title", "category", "priority", "audience", "status",
        "recipients_count", "delivered_count", "read_count", "failed_count",
        "scheduled_at", "sent_at", "created_at",
    )
    list_filter = ("status", "category", "priority", "audience", "hostel")
    search_fields = ("title", "body")
    readonly_fields = (
        "status", "sent_at", "recipients_count", "delivered_count",
        "read_count", "failed_count", "created_by", "created_at", "updated_at",
    )
    date_hierarchy = "created_at"
    inlines = [NotificationRecipientInline]
    actions = ["dispatch_now"]

    @admin.action(description="Dispatch selected notifications now")
    def dispatch_now(self, request, queryset):
        sent = 0
        for notification in queryset.exclude(status=NotificationStatus.SENT):
            dispatch(notification)
            sent += 1
        self.message_user(request, f"Dispatched {sent} notification(s).", messages.SUCCESS)


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "status", "attempts", "last_attempt_at", "next_retry_at")
    list_filter = ("status",)
    search_fields = ("recipient__user__username", "last_error")
    readonly_fields = ("recipient", "subscription", "attempts", "last_error", "last_attempt_at", "next_retry_at")
    date_hierarchy = "created_at"
