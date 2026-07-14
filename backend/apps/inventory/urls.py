from rest_framework.routers import DefaultRouter

from .views import (
    AssetViewSet,
    BrandViewSet,
    GoodsReceiptViewSet,
    InventoryDashboardViewSet,
    InventoryReportsViewSet,
    ItemCategoryViewSet,
    ItemViewSet,
    PurchaseOrderViewSet,
    StockCountViewSet,
    StockLevelViewSet,
    StockMovementViewSet,
    StorageLocationViewSet,
    UnitOfMeasureViewSet,
    VendorViewSet,
    WarehouseViewSet,
)

router = DefaultRouter()
router.register(r"categories", ItemCategoryViewSet, basename="inventory-categories")
router.register(r"brands", BrandViewSet, basename="inventory-brands")
router.register(r"units", UnitOfMeasureViewSet, basename="inventory-units")
router.register(r"items", ItemViewSet, basename="inventory-items")
router.register(r"warehouses", WarehouseViewSet, basename="inventory-warehouses")
router.register(r"locations", StorageLocationViewSet, basename="inventory-locations")
router.register(r"stock-levels", StockLevelViewSet, basename="inventory-stock-levels")
router.register(r"movements", StockMovementViewSet, basename="inventory-movements")
router.register(r"stock-counts", StockCountViewSet, basename="inventory-stock-counts")
router.register(r"vendors", VendorViewSet, basename="inventory-vendors")
router.register(r"purchase-orders", PurchaseOrderViewSet, basename="inventory-purchase-orders")
router.register(r"goods-receipts", GoodsReceiptViewSet, basename="inventory-goods-receipts")
router.register(r"assets", AssetViewSet, basename="inventory-assets")
router.register(r"dashboard", InventoryDashboardViewSet, basename="inventory-dashboard")
router.register(r"reports", InventoryReportsViewSet, basename="inventory-reports")

urlpatterns = router.urls
