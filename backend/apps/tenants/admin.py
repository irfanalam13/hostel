from django.contrib import admin
from .models import Hostel, Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price_monthly",
        "discount_percent",
        "discount_active",
        "discount_until",
        "is_public",
        "is_featured",
        "sort_order",
    )
    # Discount + visibility flags are editable straight from the list view, so an
    # admin can launch/end an offer in one click.
    list_editable = (
        "discount_percent",
        "discount_active",
        "discount_until",
        "is_public",
        "is_featured",
        "sort_order",
    )
    list_filter = ("is_public", "is_featured", "discount_active")
    search_fields = ("name",)
    fieldsets = (
        (None, {"fields": ("name", "description", "price_monthly", "currency", "period")}),
        ("Limits", {"fields": ("max_students", "max_rooms")}),
        ("Landing page", {"fields": ("features", "cta_label", "cta_href", "is_featured", "is_public", "sort_order")}),
        ("Discount", {"fields": ("discount_active", "discount_percent", "discount_label", "discount_until")}),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "hostel", "plan", "status", "start_date", "end_date")
    list_filter = ("status",)
    search_fields = ("hostel__name", "hostel__code")


@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "is_active")
    search_fields = ("name", "code")
    list_filter = ("is_active",)
    
    
    
