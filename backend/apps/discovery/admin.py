from django.contrib import admin

from .models import HostelDiscoveryProfile, Review, ReviewFlag, ReviewResponse


@admin.register(HostelDiscoveryProfile)
class HostelDiscoveryProfileAdmin(admin.ModelAdmin):
    list_display = ("hostel", "is_listed", "average_rating", "rating_count", "city", "hostel_type")
    list_filter = ("is_listed", "hostel_type", "enable_public_website")
    search_fields = ("hostel__name", "city", "district")


class ReviewFlagInline(admin.TabularInline):
    model = ReviewFlag
    extra = 0
    readonly_fields = ("reporter", "reason", "note", "created_at")


class ReviewResponseInline(admin.StackedInline):
    model = ReviewResponse
    extra = 0


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("hostel", "author", "rating", "status", "verification_method", "flag_count", "created_at")
    list_filter = ("status", "verification_method")
    search_fields = ("hostel__name", "author__username", "resident_name_snapshot", "title", "body")
    readonly_fields = ("verified_at", "verified_by", "source_resident", "source_student")
    inlines = [ReviewResponseInline, ReviewFlagInline]


@admin.register(ReviewFlag)
class ReviewFlagAdmin(admin.ModelAdmin):
    list_display = ("review", "reason", "status", "reporter", "created_at")
    list_filter = ("reason", "status")
