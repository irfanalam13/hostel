from django.contrib import admin

from .models import (
    Feature,
    FeatureCategory,
    FeatureDependency,
    FeatureOverride,
    LimitDefinition,
    LimitOverride,
    PlanFeature,
    PlanLimit,
    SubscriptionEvent,
)


class FeatureDependencyInline(admin.TabularInline):
    model = FeatureDependency
    fk_name = "feature"
    extra = 0
    autocomplete_fields = ["requires"]


@admin.register(FeatureCategory)
class FeatureCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "key", "sort_order", "is_active"]
    list_editable = ["sort_order", "is_active"]
    search_fields = ["name", "key"]
    prepopulated_fields = {"key": ("name",)}


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = [
        "label",
        "key",
        "category",
        "release_stage",
        "default_enabled",
        "is_enterprise_only",
        "is_active",
    ]
    list_filter = ["category", "release_stage", "is_enterprise_only", "is_active", "is_beta"]
    list_editable = ["default_enabled", "is_enterprise_only", "is_active"]
    search_fields = ["name", "display_name", "key", "description"]
    prepopulated_fields = {"key": ("name",)}
    autocomplete_fields = ["category"]
    inlines = [FeatureDependencyInline]
    readonly_fields = ["created_by", "updated_by"]

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(LimitDefinition)
class LimitDefinitionAdmin(admin.ModelAdmin):
    list_display = ["name", "key", "unit", "category", "default_value", "allow_unlimited", "is_active"]
    list_filter = ["category", "allow_unlimited", "is_active"]
    list_editable = ["default_value", "allow_unlimited", "is_active"]
    search_fields = ["name", "key"]
    prepopulated_fields = {"key": ("name",)}
    autocomplete_fields = ["category"]


@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = ["plan", "feature", "is_enabled"]
    list_filter = ["is_enabled", "plan", "feature__category"]
    list_editable = ["is_enabled"]
    search_fields = ["plan__name", "feature__name", "feature__key"]
    autocomplete_fields = ["plan", "feature"]


@admin.register(PlanLimit)
class PlanLimitAdmin(admin.ModelAdmin):
    list_display = ["plan", "limit", "value", "is_unlimited"]
    list_filter = ["is_unlimited", "plan", "limit"]
    list_editable = ["value", "is_unlimited"]
    search_fields = ["plan__name", "limit__name", "limit__key"]
    autocomplete_fields = ["plan", "limit"]


@admin.register(FeatureOverride)
class FeatureOverrideAdmin(admin.ModelAdmin):
    list_display = ["hostel", "feature", "is_enabled", "expires_at", "reason"]
    list_filter = ["is_enabled", "feature__category"]
    search_fields = ["hostel__name", "hostel__code", "feature__name", "feature__key", "reason"]
    autocomplete_fields = ["hostel", "feature"]
    readonly_fields = ["created_by"]

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(LimitOverride)
class LimitOverrideAdmin(admin.ModelAdmin):
    list_display = ["hostel", "limit", "value", "is_unlimited", "expires_at", "reason"]
    list_filter = ["is_unlimited", "limit"]
    search_fields = ["hostel__name", "hostel__code", "limit__name", "limit__key", "reason"]
    autocomplete_fields = ["hostel", "limit"]
    readonly_fields = ["created_by"]

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SubscriptionEvent)
class SubscriptionEventAdmin(admin.ModelAdmin):
    list_display = ["created_at", "hostel", "kind", "from_plan", "to_plan", "mrr_amount", "actor"]
    list_filter = ["kind"]
    search_fields = ["hostel__name", "hostel__code", "reason"]
    autocomplete_fields = ["hostel", "from_plan", "to_plan"]
    readonly_fields = ["created_at", "updated_at"]
