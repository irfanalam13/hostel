from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserHostel


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for custom User model."""

    list_display = (
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_staff",
        "is_active",
        "date_joined",
    )

    list_filter = (
        "role",
        "is_staff",
        "is_superuser",
        "is_active",
        "date_joined",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )

    ordering = ("-date_joined",)
    list_per_page = 25

    fieldsets = UserAdmin.fieldsets + (
        (
            "Role Information",
            {
                "fields": (
                    "role",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Role Information",
            {
                "classes": ("wide",),
                "fields": (
                    "role",
                ),
            },
        ),
    )


@admin.register(UserHostel)
class UserHostelAdmin(admin.ModelAdmin):
    """Admin configuration for User-Hostel mapping."""

    list_display = (
        "id",
        "user",
        "hostel",
        "is_active",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "is_active",
        "hostel",
    )

    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "hostel__name",
    )

    autocomplete_fields = (
        "user",
        "hostel",
    )

    ordering = ("-created_at",)
    list_per_page = 25
