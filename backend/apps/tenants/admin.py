from django.contrib import admin
from .models import Hostel  # and Tenant if you have it

@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "is_active")
    search_fields = ("name", "code")
    list_filter = ("is_active",)
    
    
    
