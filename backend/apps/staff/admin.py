from django.contrib import admin

from .models import Department, Designation, Role, StaffDocument, StaffProfile


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "full_name", "hostel", "status", "employment_type", "is_deleted")
    list_filter = ("status", "employment_type", "is_deleted")
    search_fields = ("employee_id", "first_name", "last_name", "user__username", "user__email")
    raw_id_fields = ("user", "hostel", "role", "department", "designation", "reporting_manager")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "hostel", "is_system", "is_active")
    list_filter = ("is_system", "is_active")
    search_fields = ("name", "slug")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "hostel", "is_active")
    search_fields = ("name", "code")


@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "hostel", "is_active")
    search_fields = ("title",)


@admin.register(StaffDocument)
class StaffDocumentAdmin(admin.ModelAdmin):
    list_display = ("doc_type", "title", "staff", "hostel", "expiry_date")
    list_filter = ("doc_type",)
