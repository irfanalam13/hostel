"""Inventory & Asset Management API.

All viewsets are workspace-scoped (``request.hostel``), permission-gated via
``apps.common.rbac`` (``inventory.*`` catalog) and plan-gated behind the
``inventory`` feature. Mutations are audit-logged; stock math and lifecycle
transitions live in ``apps.inventory.services``.
"""
import csv
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, ViewSet

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.common.permissions import IsHostelResolved
from apps.common.rbac import ActionPermissions
from apps.subscriptions.gates import RequiresFeature, enforce_limit

from . import services
from .models import (
    Asset,
    Brand,
    GoodsReceipt,
    Item,
    ItemCategory,
    PurchaseOrder,
    PurchaseOrderLine,
    StockCount,
    StockLevel,
    StockMovement,
    StorageLocation,
    UnitOfMeasure,
    Vendor,
    Warehouse,
)
from .serializers import (
    AdjustStockSerializer,
    AssetLifecycleEventSerializer,
    AssetSerializer,
    AssignAssetSerializer,
    BrandSerializer,
    ChangeAssetStatusSerializer,
    GoodsReceiptSerializer,
    IssueStockSerializer,
    ItemCategorySerializer,
    ItemSerializer,
    PurchaseOrderSerializer,
    ReceiveGoodsSerializer,
    StockCountSerializer,
    StockLevelSerializer,
    StockMovementSerializer,
    StorageLocationSerializer,
    TransferStockSerializer,
    UnitOfMeasureSerializer,
    VendorSerializer,
    WarehouseSerializer,
)

ZERO = Decimal("0.00")
_MONEY = DecimalField(max_digits=16, decimal_places=2)


def _money(value) -> str:
    return str(Decimal(value or 0).quantize(ZERO))


class InventoryViewSet(ModelViewSet):
    """Base for all inventory CRUD surfaces: membership + RBAC + plan feature."""

    permission_classes = [IsHostelResolved, ActionPermissions, RequiresFeature("inventory")]

    def _audit(self, action_, entity_type, obj_id, message, meta=None):
        record_event(
            self.request, action=action_, actor=self.request.user,
            hostel=self.request.hostel, entity_type=entity_type,
            entity_id=obj_id, message=message, meta=meta,
        )


_CRUD_PERMS = {
    "list": ["inventory.view"], "retrieve": ["inventory.view"],
    "create": ["inventory.create"], "update": ["inventory.edit"],
    "partial_update": ["inventory.edit"], "destroy": ["inventory.delete"],
}


# --------------------------------------------------------------------------- #
# Catalog & masters
# --------------------------------------------------------------------------- #
class ItemCategoryViewSet(InventoryViewSet):
    serializer_class = ItemCategorySerializer
    permission_map = dict(_CRUD_PERMS)
    filterset_fields = ["parent", "is_active"]
    search_fields = ["name"]

    def get_queryset(self):
        services.ensure_default_categories(self.request.hostel)
        return ItemCategory.objects.filter(hostel=self.request.hostel).select_related("parent")

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "inventory.itemcategory", obj.id,
                    f"Item category created: {obj.name}")

    def perform_update(self, serializer):
        obj = serializer.save()
        self._audit(AuditEvent.Action.UPDATE, "inventory.itemcategory", obj.id,
                    f"Item category updated: {obj.name}")

    def perform_destroy(self, instance):
        if instance.is_system:
            raise ValidationError({"detail": "System categories cannot be deleted (deactivate instead)."})
        name, oid = instance.name, instance.id
        instance.delete()
        self._audit(AuditEvent.Action.DELETE, "inventory.itemcategory", oid,
                    f"Item category deleted: {name}")


class BrandViewSet(InventoryViewSet):
    serializer_class = BrandSerializer
    permission_map = dict(_CRUD_PERMS)
    filterset_fields = ["is_active"]
    search_fields = ["name", "manufacturer"]

    def get_queryset(self):
        return Brand.objects.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "inventory.brand", obj.id, f"Brand created: {obj.name}")


class UnitOfMeasureViewSet(InventoryViewSet):
    serializer_class = UnitOfMeasureSerializer
    permission_map = dict(_CRUD_PERMS)
    search_fields = ["name", "symbol"]

    def get_queryset(self):
        services.ensure_default_uom(self.request.hostel)
        return UnitOfMeasure.objects.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "inventory.unitofmeasure", obj.id,
                    f"Unit created: {obj.name}")

    def perform_destroy(self, instance):
        if instance.is_system:
            raise ValidationError({"detail": "System units cannot be deleted."})
        instance.delete()


class ItemViewSet(InventoryViewSet):
    serializer_class = ItemSerializer
    permission_map = {
        **_CRUD_PERMS,
        "adjust_stock": ["inventory.adjust"],
        "transfer": ["inventory.transfer"],
        "issue": ["inventory.adjust"],
        "movements": ["inventory.view"],
        "forecast": ["inventory.view"],
    }
    filterset_fields = ["category", "brand", "item_type", "is_active"]
    search_fields = ["name", "item_code", "sku", "barcode"]
    ordering_fields = ["name", "created_at", "average_cost"]

    def get_queryset(self):
        return (
            Item.objects.filter(hostel=self.request.hostel, is_deleted=False)
            .select_related("category", "brand", "stock_uom")
        )

    def perform_create(self, serializer):
        enforce_limit(self.request.hostel, "max_inventory_items")
        obj = serializer.save(
            hostel=self.request.hostel,
            item_code=services.next_number(self.request.hostel, "item"),
        )
        self._audit(AuditEvent.Action.CREATE, "inventory.item", obj.id, f"Item created: {obj.name}")

    def perform_update(self, serializer):
        obj = serializer.save()
        self._audit(AuditEvent.Action.UPDATE, "inventory.item", obj.id, f"Item updated: {obj.name}")

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.is_active = False
        instance.save(update_fields=["is_deleted", "is_active", "updated_at"])
        self._audit(AuditEvent.Action.DELETE, "inventory.item", instance.id,
                    f"Item archived: {instance.name}")

    @action(detail=True, methods=["post"], url_path="adjust-stock")
    def adjust_stock(self, request, pk=None):
        item = self.get_object()
        serializer = AdjustStockSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        movement = services.adjust_stock(
            hostel=request.hostel, item=item, warehouse=data["warehouse"],
            location=data.get("location"), target_quantity=data["target_quantity"],
            actor=request.user, reason=data.get("reason", ""),
        )
        self._audit(AuditEvent.Action.UPDATE, "inventory.item", item.id,
                    f"Stock adjusted: {item.name} → {data['target_quantity']}")
        return Response(
            StockMovementSerializer(movement).data if movement else {"detail": "No change."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        item = self.get_object()
        serializer = TransferStockSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            out, into = services.transfer_stock(
                hostel=request.hostel, item=item, from_warehouse=data["from_warehouse"],
                to_warehouse=data["to_warehouse"], quantity=data["quantity"],
                actor=request.user, note=data.get("note", ""),
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        self._audit(AuditEvent.Action.UPDATE, "inventory.item", item.id,
                    f"Stock transferred: {item.name} ×{data['quantity']}")
        return Response(StockMovementSerializer([out, into], many=True).data)

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        """Issue/allocate/consume stock out to a room/bed and optional occupant."""
        item = self.get_object()
        serializer = IssueStockSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            movement = services.apply_movement(
                hostel=request.hostel, item=item, warehouse=data["warehouse"],
                location=data.get("location"), quantity=data["quantity"],
                movement_type=data["movement_type"], direction=StockMovement.Direction.OUT,
                actor=request.user, reason=data.get("reason", ""),
                room=data.get("room"), bed=data.get("bed"),
                resident=data.get("resident"), student=data.get("student"),
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        self._audit(AuditEvent.Action.UPDATE, "inventory.item", item.id,
                    f"Stock issued: {item.name} ×{data['quantity']}")
        return Response(StockMovementSerializer(movement).data)

    @action(detail=True, methods=["get"])
    def movements(self, request, pk=None):
        item = self.get_object()
        qs = item.movements.all()[:200]
        return Response(StockMovementSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"])
    def forecast(self, request, pk=None):
        item = self.get_object()
        return Response(services.forecast_consumption(item))


# --------------------------------------------------------------------------- #
# Warehousing
# --------------------------------------------------------------------------- #
class WarehouseViewSet(InventoryViewSet):
    serializer_class = WarehouseSerializer
    permission_map = dict(_CRUD_PERMS)
    filterset_fields = ["warehouse_type", "is_active"]
    search_fields = ["name"]

    def get_queryset(self):
        services.ensure_default_warehouse(self.request.hostel)
        return Warehouse.objects.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "inventory.warehouse", obj.id,
                    f"Warehouse created: {obj.name}")


class StorageLocationViewSet(InventoryViewSet):
    serializer_class = StorageLocationSerializer
    permission_map = dict(_CRUD_PERMS)
    filterset_fields = ["warehouse", "is_active"]
    search_fields = ["name", "zone", "rack", "shelf", "bin"]

    def get_queryset(self):
        return StorageLocation.objects.filter(hostel=self.request.hostel).select_related("warehouse")

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "inventory.storagelocation", obj.id,
                    f"Storage location created: {obj.name}")


class StockLevelViewSet(ReadOnlyModelViewSet):
    """Read-only on-hand view. Quantities are only ever changed via movements."""

    permission_classes = [IsHostelResolved, ActionPermissions, RequiresFeature("inventory")]
    permission_map = {"list": ["inventory.view"], "retrieve": ["inventory.view"]}
    serializer_class = StockLevelSerializer
    filterset_fields = ["item", "warehouse"]

    def get_queryset(self):
        return (
            StockLevel.objects.filter(hostel=self.request.hostel)
            .select_related("item", "warehouse", "location")
        )


class StockMovementViewSet(InventoryViewSet):
    """Movements are append-only: list + retrieve + create (a manual entry)."""

    serializer_class = StockMovementSerializer
    http_method_names = ["get", "post", "head", "options"]
    permission_map = {
        "list": ["inventory.view"], "retrieve": ["inventory.view"],
        "create": ["inventory.adjust"],
    }
    filterset_fields = ["item", "warehouse", "movement_type", "direction"]
    search_fields = ["reference", "reason"]
    ordering_fields = ["occurred_at", "created_at"]

    def get_queryset(self):
        return (
            StockMovement.objects.filter(hostel=self.request.hostel)
            .select_related("item", "warehouse")
        )

    def perform_create(self, serializer):
        data = serializer.validated_data
        try:
            movement = services.apply_movement(
                hostel=self.request.hostel, item=data["item"], warehouse=data["warehouse"],
                location=data.get("location"), quantity=data["quantity"],
                movement_type=data["movement_type"], actor=self.request.user,
                reason=data.get("reason", ""), note=data.get("note", ""),
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        serializer.instance = movement
        self._audit(AuditEvent.Action.CREATE, "inventory.stockmovement", movement.id,
                    f"Movement {movement.reference}: {movement.movement_type}")


class StockCountViewSet(InventoryViewSet):
    serializer_class = StockCountSerializer
    permission_map = {
        **_CRUD_PERMS,
        "create": ["inventory.adjust"],
        "complete": ["inventory.adjust"],
    }
    filterset_fields = ["warehouse", "status"]

    def get_queryset(self):
        return StockCount.objects.filter(hostel=self.request.hostel).select_related("warehouse")

    def perform_create(self, serializer):
        obj = serializer.save(
            hostel=self.request.hostel,
            reference=services.next_number(self.request.hostel, "stock_count"),
            created_by=self.request.user,
        )
        self._audit(AuditEvent.Action.CREATE, "inventory.stockcount", obj.id,
                    f"Stock count started: {obj.reference}")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        count = self.get_object()
        if count.status != StockCount.Status.DRAFT:
            raise ValidationError({"detail": "Only draft counts can be completed."})
        services.complete_stock_count(count, actor=request.user)
        self._audit(AuditEvent.Action.UPDATE, "inventory.stockcount", count.id,
                    f"Stock count completed: {count.reference}")
        return Response(StockCountSerializer(count).data)


# --------------------------------------------------------------------------- #
# Procurement
# --------------------------------------------------------------------------- #
class VendorViewSet(InventoryViewSet):
    serializer_class = VendorSerializer
    permission_map = dict(_CRUD_PERMS)
    filterset_fields = ["is_active", "is_blacklisted"]
    search_fields = ["company_name", "contact_person", "email", "phone"]
    ordering_fields = ["company_name", "rating", "created_at"]

    def get_queryset(self):
        return Vendor.objects.filter(hostel=self.request.hostel, is_deleted=False)

    def perform_create(self, serializer):
        obj = serializer.save(
            hostel=self.request.hostel,
            vendor_code=services.next_number(self.request.hostel, "vendor"),
        )
        self._audit(AuditEvent.Action.CREATE, "inventory.vendor", obj.id,
                    f"Vendor created: {obj.company_name}")

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.is_active = False
        instance.save(update_fields=["is_deleted", "is_active", "updated_at"])
        self._audit(AuditEvent.Action.DELETE, "inventory.vendor", instance.id,
                    f"Vendor archived: {instance.company_name}")


class PurchaseOrderViewSet(InventoryViewSet):
    serializer_class = PurchaseOrderSerializer
    permission_map = {
        **_CRUD_PERMS,
        "submit": ["inventory.edit"],
        "approve": ["inventory.approve"],
        "cancel": ["inventory.edit"],
        "receive": ["inventory.approve"],
    }
    filterset_fields = ["vendor", "status", "warehouse"]
    search_fields = ["po_number", "notes"]
    ordering_fields = ["order_date", "total", "created_at"]

    def get_queryset(self):
        return (
            PurchaseOrder.objects.filter(hostel=self.request.hostel)
            .select_related("vendor", "warehouse").prefetch_related("lines__item")
        )

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel, created_by=self.request.user)
        self._audit(AuditEvent.Action.CREATE, "inventory.purchaseorder", obj.id,
                    f"Purchase order created: {obj.po_number}", meta={"total": str(obj.total)})

    def perform_update(self, serializer):
        if serializer.instance.status not in (
            PurchaseOrder.Status.DRAFT, PurchaseOrder.Status.PENDING_APPROVAL
        ):
            raise ValidationError({"detail": "Only draft/pending purchase orders can be edited."})
        obj = serializer.save()
        self._audit(AuditEvent.Action.UPDATE, "inventory.purchaseorder", obj.id,
                    f"Purchase order updated: {obj.po_number}")

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        po = self.get_object()
        services.submit_po(po)
        self._audit(AuditEvent.Action.UPDATE, "inventory.purchaseorder", po.id,
                    f"Purchase order submitted: {po.po_number}")
        return Response(self.get_serializer(po).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        po = self.get_object()
        services.approve_po(po, actor=request.user)
        self._audit(AuditEvent.Action.UPDATE, "inventory.purchaseorder", po.id,
                    f"Purchase order approved: {po.po_number}")
        return Response(self.get_serializer(po).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        po = self.get_object()
        services.cancel_po(po)
        self._audit(AuditEvent.Action.UPDATE, "inventory.purchaseorder", po.id,
                    f"Purchase order cancelled: {po.po_number}")
        return Response(self.get_serializer(po).data)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        po = self.get_object()
        serializer = ReceiveGoodsSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        warehouse = (
            Warehouse.objects.filter(hostel=request.hostel, id=data["warehouse"]).first()
            if data.get("warehouse") else (po.warehouse or services.default_warehouse(request.hostel))
        )
        if warehouse is None:
            raise ValidationError({"warehouse": "A warehouse is required to receive goods."})

        resolved_lines = []
        for row in data["lines"]:
            item = Item.objects.filter(hostel=request.hostel, id=row["item"]).first()
            if item is None:
                raise ValidationError({"item": f"Unknown item {row['item']}."})
            po_line = (
                PurchaseOrderLine.objects.filter(
                    hostel=request.hostel, purchase_order=po, id=row["po_line"]
                ).first()
                if row.get("po_line") else None
            )
            location = (
                StorageLocation.objects.filter(hostel=request.hostel, id=row["location"]).first()
                if row.get("location") else None
            )
            resolved_lines.append({
                "item": item, "po_line": po_line, "quantity": row["quantity"],
                "unit_cost": row.get("unit_cost"), "batch_number": row.get("batch_number", ""),
                "location": location,
            })

        grn = services.receive_goods(
            po=po, warehouse=warehouse, lines=resolved_lines, actor=request.user,
            received_date=data.get("received_date"), note=data.get("note", ""),
        )
        self._audit(AuditEvent.Action.CREATE, "inventory.goodsreceipt", grn.id,
                    f"Goods received: {grn.grn_number} against {po.po_number}")
        return Response(GoodsReceiptSerializer(grn).data, status=status.HTTP_201_CREATED)


class GoodsReceiptViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsHostelResolved, ActionPermissions, RequiresFeature("inventory")]
    permission_map = {"list": ["inventory.view"], "retrieve": ["inventory.view"]}
    serializer_class = GoodsReceiptSerializer
    filterset_fields = ["purchase_order", "warehouse"]

    def get_queryset(self):
        return (
            GoodsReceipt.objects.filter(hostel=self.request.hostel)
            .select_related("purchase_order", "warehouse").prefetch_related("lines__item")
        )


# --------------------------------------------------------------------------- #
# Assets
# --------------------------------------------------------------------------- #
class AssetViewSet(InventoryViewSet):
    serializer_class = AssetSerializer
    permission_map = {
        **_CRUD_PERMS,
        "assign": ["inventory.edit"],
        "return_asset": ["inventory.edit"],
        "change_status": ["inventory.edit"],
        "depreciate": ["inventory.edit"],
        "history": ["inventory.view"],
    }
    filterset_fields = ["category", "status", "condition", "vendor", "warehouse"]
    search_fields = ["name", "asset_tag", "serial_number", "barcode"]
    ordering_fields = ["name", "purchase_date", "purchase_cost", "created_at"]

    def get_queryset(self):
        return (
            Asset.objects.filter(hostel=self.request.hostel, is_deleted=False)
            .select_related("category", "vendor", "warehouse", "accounting_asset")
        )

    def perform_create(self, serializer):
        obj = serializer.save(
            hostel=self.request.hostel,
            asset_tag=services.next_number(self.request.hostel, "asset"),
        )
        self._audit(AuditEvent.Action.CREATE, "inventory.asset", obj.id,
                    f"Asset created: {obj.name}")

    def perform_update(self, serializer):
        obj = serializer.save()
        self._audit(AuditEvent.Action.UPDATE, "inventory.asset", obj.id,
                    f"Asset updated: {obj.name}")

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted", "updated_at"])
        self._audit(AuditEvent.Action.DELETE, "inventory.asset", instance.id,
                    f"Asset archived: {instance.name}")

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        asset = self.get_object()
        serializer = AssignAssetSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        services.assign_asset(asset=asset, actor=request.user, **serializer.validated_data)
        self._audit(AuditEvent.Action.UPDATE, "inventory.asset", asset.id,
                    f"Asset assigned: {asset.name}")
        return Response(self.get_serializer(asset).data)

    @action(detail=True, methods=["post"], url_path="return")
    def return_asset(self, request, pk=None):
        asset = self.get_object()
        services.return_asset(asset=asset, actor=request.user, note=request.data.get("note", ""))
        self._audit(AuditEvent.Action.UPDATE, "inventory.asset", asset.id,
                    f"Asset returned: {asset.name}")
        return Response(self.get_serializer(asset).data)

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        asset = self.get_object()
        serializer = ChangeAssetStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        services.change_asset_status(
            asset=asset, status=data["status"], actor=request.user,
            note=data.get("note", ""), cost=data.get("cost") or Decimal("0.00"),
        )
        self._audit(AuditEvent.Action.UPDATE, "inventory.asset", asset.id,
                    f"Asset status → {data['status']}: {asset.name}")
        return Response(self.get_serializer(asset).data)

    @action(detail=True, methods=["post"])
    def depreciate(self, request, pk=None):
        asset = self.get_object()
        try:
            entry = services.run_asset_depreciation(asset=asset, actor=request.user)
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        self._audit(AuditEvent.Action.UPDATE, "inventory.asset", asset.id,
                    f"Depreciation posted: {asset.name}")
        return Response({"detail": "Depreciation posted.", "entry_id": str(getattr(entry, "id", ""))})

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        asset = self.get_object()
        return Response(
            AssetLifecycleEventSerializer(asset.lifecycle_events.all(), many=True).data
        )


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
class InventoryDashboardViewSet(ViewSet):
    permission_classes = [IsHostelResolved, ActionPermissions, RequiresFeature("inventory")]
    permission_map = {"summary": ["inventory.view"]}

    @action(detail=False, methods=["get"])
    def summary(self, request):
        hostel = request.hostel
        items = Item.objects.filter(hostel=hostel, is_deleted=False)
        levels = StockLevel.objects.filter(hostel=hostel)

        inventory_value = levels.aggregate(
            v=Coalesce(Sum(F("quantity_on_hand") * F("item__average_cost"), output_field=_MONEY),
                       Value(ZERO, output_field=_MONEY))
        )["v"]

        # Per-item on-hand for stock-status buckets.
        on_hand_by_item = {
            row["item"]: row["q"]
            for row in levels.values("item").annotate(q=Sum("quantity_on_hand"))
        }
        low = out = over = 0
        for item in items.only("id", "reorder_level", "max_stock"):
            q = on_hand_by_item.get(item.id, ZERO) or ZERO
            if q <= 0:
                out += 1
            elif item.reorder_level and q <= item.reorder_level:
                low += 1
            if item.max_stock and q > item.max_stock:
                over += 1

        assets = Asset.objects.filter(hostel=hostel, is_deleted=False)
        pos = PurchaseOrder.objects.filter(hostel=hostel)

        since = timezone.now() - timedelta(days=180)
        movement_trend = (
            StockMovement.objects.filter(hostel=hostel, occurred_at__gte=since)
            .annotate(month=TruncMonth("occurred_at"))
            .values("month", "direction")
            .annotate(qty=Sum("quantity"))
            .order_by("month")
        )
        by_category = (
            items.values("category__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:8]
        )
        recent_movements = (
            StockMovement.objects.filter(hostel=hostel)
            .select_related("item", "warehouse")[:10]
        )

        return Response({
            "totals": {
                "inventory_value": _money(inventory_value),
                "total_items": items.count(),
                "active_items": items.filter(is_active=True).count(),
                "total_assets": assets.count(),
                "active_assets": assets.filter(status=Asset.Status.AVAILABLE).count()
                                 + assets.filter(status=Asset.Status.ASSIGNED).count(),
                "inactive_assets": assets.filter(
                    status__in=[Asset.Status.RETIRED, Asset.Status.DISPOSED, Asset.Status.LOST]
                ).count(),
                "maintenance_assets": assets.filter(status=Asset.Status.IN_MAINTENANCE).count(),
                "damaged_assets": assets.filter(status=Asset.Status.DAMAGED).count(),
                "low_stock": low,
                "out_of_stock": out,
                "overstock": over,
                "total_vendors": Vendor.objects.filter(hostel=hostel, is_deleted=False).count(),
                "open_purchase_orders": pos.exclude(
                    status__in=[PurchaseOrder.Status.CLOSED, PurchaseOrder.Status.CANCELLED,
                                PurchaseOrder.Status.FULLY_RECEIVED]
                ).count(),
                "pending_deliveries": pos.filter(
                    status__in=[PurchaseOrder.Status.ORDERED,
                                PurchaseOrder.Status.PARTIALLY_RECEIVED]
                ).count(),
            },
            "movement_trend": [
                {"month": r["month"].strftime("%Y-%m") if r["month"] else None,
                 "direction": r["direction"], "quantity": str(r["qty"] or 0)}
                for r in movement_trend
            ],
            "by_category": [
                {"category": r["category__name"] or "Uncategorized", "count": r["count"]}
                for r in by_category
            ],
            "recent_movements": StockMovementSerializer(recent_movements, many=True).data,
        })


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #
class InventoryReportsViewSet(ViewSet):
    permission_classes = [IsHostelResolved, ActionPermissions, RequiresFeature("inventory")]
    permission_map = {
        "stock_summary": ["inventory.view"],
        "valuation": ["inventory.view"],
        "low_stock": ["inventory.view"],
        "export": ["inventory.export"],
    }

    def _rows_stock_summary(self, hostel):
        levels = (
            StockLevel.objects.filter(hostel=hostel)
            .values("item__item_code", "item__name", "warehouse__name")
            .annotate(qty=Sum("quantity_on_hand"))
            .order_by("item__name")
        )
        return (
            ["Item Code", "Item", "Warehouse", "On Hand"],
            [[r["item__item_code"], r["item__name"], r["warehouse__name"], str(r["qty"] or 0)]
             for r in levels],
        )

    @action(detail=False, methods=["get"], url_path="stock-summary")
    def stock_summary(self, request):
        headers, rows = self._rows_stock_summary(request.hostel)
        return Response({"headers": headers, "rows": rows})

    @action(detail=False, methods=["get"])
    def valuation(self, request):
        rows = (
            Item.objects.filter(hostel=request.hostel, is_deleted=False)
            .annotate(on_hand=Coalesce(Sum("stock_levels__quantity_on_hand"),
                                       Value(Decimal("0"), output_field=DecimalField())))
            .values("item_code", "name", "average_cost", "on_hand")
            .order_by("name")
        )
        data = [
            {"item_code": r["item_code"], "name": r["name"],
             "average_cost": _money(r["average_cost"]), "on_hand": str(r["on_hand"] or 0),
             "value": _money((r["average_cost"] or ZERO) * (r["on_hand"] or ZERO))}
            for r in rows
        ]
        return Response({"items": data,
                         "total_value": _money(sum(Decimal(d["value"]) for d in data))})

    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        items = Item.objects.filter(hostel=request.hostel, is_deleted=False, reorder_level__gt=0)
        result = []
        for item in items:
            on_hand = services.item_on_hand(item)
            if on_hand <= item.reorder_level:
                result.append({
                    "item_code": item.item_code, "name": item.name,
                    "on_hand": str(on_hand), "reorder_level": str(item.reorder_level),
                    "status": "out_of_stock" if on_hand <= 0 else "low",
                })
        return Response({"items": result})

    @action(detail=False, methods=["get"])
    def export(self, request):
        """Export a report as CSV or Excel. ``?type=stock-summary&fmt=csv``.

        The output format uses ``fmt`` (not ``format``) to avoid colliding with
        DRF's content-negotiation ``format`` query override.
        """
        report = request.query_params.get("type", "stock-summary")
        fmt = request.query_params.get("fmt", "csv")
        builders = {"stock-summary": self._rows_stock_summary}
        builder = builders.get(report)
        if builder is None:
            raise ValidationError({"type": f"Unknown report '{report}'."})
        headers, rows = builder(request.hostel)

        record_event(
            request, action=AuditEvent.Action.EXPORT, actor=request.user,
            hostel=request.hostel, entity_type="inventory.report",
            entity_id=report, message=f"Inventory report exported: {report} ({fmt})",
        )

        if fmt == "xlsx":
            from apps.exports.excel import wb_from_rows

            wb = wb_from_rows(report, headers, rows)
            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = f'attachment; filename="inventory-{report}.xlsx"'
            wb.save(response)
            return response

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="inventory-{report}.csv"'
        writer = csv.writer(response)
        writer.writerow(headers)
        writer.writerows(rows)
        return response
