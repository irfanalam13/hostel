from django.contrib import admin

from .models import AiUsage, Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "hostel", "user", "title", "message_count", "last_message_at")
    list_filter = ("agent", "is_archived")
    search_fields = ("title",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "provider", "model", "created_at")
    list_filter = ("role", "provider")


@admin.register(AiUsage)
class AiUsageAdmin(admin.ModelAdmin):
    list_display = ("id", "hostel", "kind", "model", "tokens_total", "latency_ms", "success", "created_at")
    list_filter = ("kind", "provider", "success")
