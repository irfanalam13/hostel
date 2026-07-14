from django.contrib import admin

from .models import (
    Asset,
    Brand,
    GoodsReceipt,
    Item,
    ItemCategory,
    PurchaseOrder,
    StockLevel,
    StockMovement,
    UnitOfMeasure,
    Vendor,
    Warehouse,
)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("item_code", "name", "item_type", "hostel", "is_active")
    list_filter = ("item_type", "is_active", "hostel")
    search_fields = ("item_code", "name", "sku", "barcode")


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("asset_tag", "name", "status", "condition", "hostel")
    list_filter = ("status", "condition", "hostel")
    search_fields = ("asset_tag", "name", "serial_number")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("po_number", "vendor", "status", "total", "hostel")
    list_filter = ("status", "hostel")
    search_fields = ("po_number",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("reference", "item", "movement_type", "direction", "quantity", "hostel")
    list_filter = ("movement_type", "direction", "hostel")
    search_fields = ("reference",)


admin.site.register([
    ItemCategory, Brand, UnitOfMeasure, Warehouse, StockLevel, Vendor, GoodsReceipt,
])
