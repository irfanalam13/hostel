from django.contrib import admin

from .models import Faq, Lead, LegalDocument, SitePage


@admin.register(Faq)
class FaqAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "order", "is_published")
    list_editable = ("order", "is_published")
    list_filter = ("is_published", "category")
    search_fields = ("question", "answer")


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ("slug", "title", "last_updated", "is_published")
    list_editable = ("is_published",)
    search_fields = ("slug", "title")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(SitePage)
class SitePageAdmin(admin.ModelAdmin):
    list_display = ("slug", "title", "is_published")
    list_editable = ("is_published",)
    search_fields = ("slug", "title")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "organization", "kind", "is_handled", "created_at")
    list_editable = ("is_handled",)
    list_filter = ("kind", "is_handled", "created_at")
    search_fields = ("name", "email", "organization", "message")
    readonly_fields = ("name", "email", "organization", "message", "kind", "source", "created_at", "updated_at")

    def has_add_permission(self, request):
        # Leads only arrive via the public form, never created by hand.
        return False
