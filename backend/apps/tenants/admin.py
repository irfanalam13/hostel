from django.contrib import admin
from apps.subscriptions.models import PlanFeature, PlanLimit
from .models import Hostel, Plan, Subscription, Testimonial


class PlanFeatureInline(admin.TabularInline):
    model = PlanFeature
    extra = 0
    autocomplete_fields = ["feature"]


class PlanLimitInline(admin.TabularInline):
    model = PlanLimit
    extra = 0
    autocomplete_fields = ["limit"]


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = (
        "author_name",
        "author_role",
        "rating",
        "is_approved",
        "is_featured",
        "sort_order",
        "created_at",
    )
    # Approve + feature ("purify") straight from the list view.
    list_editable = ("is_approved", "is_featured", "sort_order")
    list_filter = ("is_approved", "is_featured", "rating")
    search_fields = ("author_name", "author_role", "quote")
    actions = ("approve_selected", "feature_selected", "unfeature_selected")

    @admin.action(description="Approve selected reviews")
    def approve_selected(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description="Feature selected on landing (also approves)")
    def feature_selected(self, request, queryset):
        queryset.update(is_approved=True, is_featured=True)

    @admin.action(description="Remove from landing (unfeature)")
    def unfeature_selected(self, request, queryset):
        queryset.update(is_featured=False)


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
    list_filter = ("visibility", "is_active", "is_archived", "is_public", "is_featured", "discount_active")
    search_fields = ("name", "slug")
    readonly_fields = ("slug",)
    inlines = [PlanFeatureInline, PlanLimitInline]
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "notes", "version")}),
        ("Pricing", {"fields": ("price_monthly", "price_yearly", "price_lifetime", "currency", "period", "billing_interval", "tax_percent")}),
        ("Trial & billing", {"fields": ("trial_days", "grace_period_days")}),
        ("Legacy limits (superseded by Plan limits below)", {"fields": ("max_students", "max_rooms")}),
        ("Presentation", {"fields": ("badge", "theme_color", "visibility", "is_recommended", "is_active", "is_archived", "is_featured", "is_public", "sort_order")}),
        ("Landing page", {"fields": ("features", "cta_label", "cta_href")}),
        ("Discount", {"fields": ("discount_active", "discount_percent", "discount_label", "discount_until")}),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "hostel", "plan", "status", "start_date", "end_date")
    list_filter = ("status",)
    search_fields = ("hostel__name", "hostel__code")


@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "code", "status", "is_active", "is_deleted")
    search_fields = ("name", "code", "slug")
    list_filter = ("is_active", "status", "is_deleted")
    readonly_fields = ("slug", "code")
    
    
    
