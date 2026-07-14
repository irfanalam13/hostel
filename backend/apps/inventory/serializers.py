"""Inventory serializers.

Every relational field is constrained to the request's workspace at
construction time (``_HostelScopedRelationsMixin``) so a payload can never
reference another tenant's rows. On-hand quantities, document numbers, costs and
statuses are read-only — the service layer owns them.
"""
from rest_framework import serializers

from apps.residents.models import Resident
from apps.rooms.models import Bed, Room
from apps.staff.models import StaffProfile
from apps.students.models import Student

from .models import (
    Asset,
    AssetAssignment,
    AssetLifecycleEvent,
    Brand,
    GoodsReceipt,
    GoodsReceiptLine,
    Item,
    ItemCategory,
    ItemDocument,
    ItemImage,
    PurchaseOrder,
    PurchaseOrderLine,
    StockCount,
    StockCountLine,
    StockLevel,
    StockMovement,
    StorageLocation,
    UnitOfMeasure,
    Vendor,
    Warehouse,
)


class _HostelScopedRelationsMixin:
    """Restrict the querysets of listed relational fields to ``request.hostel``."""

    scoped_relations: dict = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        hostel = getattr(request, "hostel", None)
        for field_name, model in self.scoped_relations.items():
            field = self.fields.get(field_name)
            if field is not None and hostel is not None:
                field.queryset = model.objects.filter(hostel=hostel)


# --------------------------------------------------------------------------- #
# Catalog & masters
# --------------------------------------------------------------------------- #
class ItemCategorySerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"parent": ItemCategory}
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)

    class Meta:
        model = ItemCategory
        fields = [
            "id", "name", "parent", "parent_name", "description",
            "is_system", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = [
            "id", "name", "manufacturer", "website", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UnitOfMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = [
            "id", "name", "symbol", "factor", "is_base", "is_system",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]


class ItemImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemImage
        fields = ["id", "item", "image", "caption", "created_at"]
        read_only_fields = ["id", "created_at"]


class ItemDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemDocument
        fields = ["id", "item", "file", "kind", "title", "created_at"]
        read_only_fields = ["id", "created_at"]


class ItemSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {
        "category": ItemCategory, "brand": Brand,
        "stock_uom": UnitOfMeasure, "purchase_uom": UnitOfMeasure,
        "default_warehouse": Warehouse,
    }
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    brand_name = serializers.CharField(source="brand.name", read_only=True, default=None)
    on_hand = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = [
            "id", "item_code", "sku", "barcode", "qr_code", "name", "description",
            "category", "category_name", "brand", "brand_name", "model",
            "manufacturer", "item_type", "stock_uom", "purchase_uom",
            "min_stock", "max_stock", "reorder_level", "safety_stock",
            "purchase_price", "selling_price", "average_cost", "standard_cost",
            "tax_rate", "discount", "valuation_method",
            "track_serial", "track_batch", "track_expiry", "warranty_months",
            "default_warehouse", "rfid_tag", "is_active", "on_hand",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "item_code", "average_cost", "on_hand", "created_at", "updated_at",
        ]

    def get_on_hand(self, obj):
        from . import services

        return str(services.item_on_hand(obj))


# --------------------------------------------------------------------------- #
# Warehousing
# --------------------------------------------------------------------------- #
class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = [
            "id", "name", "warehouse_type", "capacity", "temperature",
            "security_level", "address", "is_default", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StorageLocationSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"warehouse": Warehouse}
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True, default=None)

    class Meta:
        model = StorageLocation
        fields = [
            "id", "warehouse", "warehouse_name", "name", "zone", "rack",
            "shelf", "bin", "room", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StockLevelSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True, default=None)
    item_code = serializers.CharField(source="item.item_code", read_only=True, default=None)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True, default=None)
    quantity_available = serializers.DecimalField(
        max_digits=14, decimal_places=3, read_only=True
    )

    class Meta:
        model = StockLevel
        fields = [
            "id", "item", "item_name", "item_code", "warehouse", "warehouse_name",
            "location", "quantity_on_hand", "quantity_reserved", "quantity_allocated",
            "quantity_available", "created_at", "updated_at",
        ]
        read_only_fields = fields


class StockMovementSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"item": Item, "warehouse": Warehouse, "location": StorageLocation}
    item_name = serializers.CharField(source="item.name", read_only=True, default=None)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True, default=None)

    class Meta:
        model = StockMovement
        fields = [
            "id", "reference", "item", "item_name", "warehouse", "warehouse_name",
            "location", "movement_type", "direction", "quantity", "unit_cost",
            "source_type", "source_id", "room", "bed", "resident", "student",
            "complaint", "reason", "note", "occurred_at", "created_at",
        ]
        read_only_fields = [
            "id", "reference", "direction", "unit_cost", "source_type",
            "source_id", "created_at",
        ]


class StockCountLineSerializer(serializers.ModelSerializer):
    variance = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)

    class Meta:
        model = StockCountLine
        fields = [
            "id", "item", "location", "system_quantity", "counted_quantity", "variance",
        ]
        read_only_fields = ["id", "system_quantity", "variance"]


class StockCountSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"warehouse": Warehouse}
    lines = StockCountLineSerializer(many=True, required=False)

    class Meta:
        model = StockCount
        fields = [
            "id", "reference", "warehouse", "status", "note", "lines",
            "completed_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "reference", "status", "completed_at", "created_at", "updated_at"]

    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        hostel = validated_data["hostel"]
        count = StockCount.objects.create(**validated_data)
        from . import services

        for line in lines:
            item = line["item"]
            location = line.get("location")
            level = StockLevel.objects.filter(
                hostel=hostel, item=item, warehouse=count.warehouse, location=location
            ).first()
            system_qty = level.quantity_on_hand if level else 0
            StockCountLine.objects.create(
                hostel=hostel, stock_count=count, item=item, location=location,
                system_quantity=system_qty, counted_quantity=line["counted_quantity"],
            )
        return count


# --------------------------------------------------------------------------- #
# Procurement
# --------------------------------------------------------------------------- #
class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            "id", "vendor_code", "company_name", "contact_person", "email",
            "phone", "website", "address", "tax_number", "pan_vat",
            "payment_terms", "bank_details", "rating", "is_blacklisted",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "vendor_code", "created_at", "updated_at"]


class PurchaseOrderLineSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"item": Item}
    item_name = serializers.CharField(source="item.name", read_only=True, default=None)
    outstanding_quantity = serializers.DecimalField(
        max_digits=14, decimal_places=3, read_only=True
    )

    class Meta:
        model = PurchaseOrderLine
        fields = [
            "id", "item", "item_name", "description", "ordered_quantity",
            "received_quantity", "unit_price", "tax_rate", "discount",
            "line_total", "outstanding_quantity",
        ]
        read_only_fields = ["id", "received_quantity", "line_total", "outstanding_quantity"]


class PurchaseOrderSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"vendor": Vendor, "warehouse": Warehouse}
    lines = PurchaseOrderLineSerializer(many=True)
    vendor_name = serializers.CharField(source="vendor.company_name", read_only=True, default=None)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "po_number", "vendor", "vendor_name", "warehouse", "status",
            "order_date", "expected_date", "subtotal", "tax_total",
            "discount_total", "total", "notes", "approved_at", "lines",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "po_number", "status", "subtotal", "tax_total", "discount_total",
            "total", "approved_at", "created_at", "updated_at",
        ]

    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        from . import services

        po = PurchaseOrder.objects.create(
            po_number=services.next_number(validated_data["hostel"], "purchase_order"),
            **validated_data,
        )
        for line in lines:
            PurchaseOrderLine.objects.create(hostel=po.hostel, purchase_order=po, **line)
        services.recalc_po_totals(po)
        return po

    def update(self, instance, validated_data):
        lines = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines is not None:
            instance.lines.all().delete()
            for line in lines:
                PurchaseOrderLine.objects.create(
                    hostel=instance.hostel, purchase_order=instance, **line
                )
        from . import services

        services.recalc_po_totals(instance)
        return instance


class GoodsReceiptLineSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"item": Item, "po_line": PurchaseOrderLine, "location": StorageLocation}
    item_name = serializers.CharField(source="item.name", read_only=True, default=None)

    class Meta:
        model = GoodsReceiptLine
        fields = [
            "id", "po_line", "item", "item_name", "quantity", "unit_cost",
            "batch_number", "location",
        ]
        read_only_fields = ["id"]


class GoodsReceiptSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"purchase_order": PurchaseOrder, "warehouse": Warehouse}
    lines = GoodsReceiptLineSerializer(many=True, read_only=True)
    grn_number = serializers.CharField(read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = [
            "id", "grn_number", "purchase_order", "warehouse", "received_date",
            "note", "lines", "created_at",
        ]
        read_only_fields = ["id", "grn_number", "lines", "created_at"]


# --------------------------------------------------------------------------- #
# Assets
# --------------------------------------------------------------------------- #
class AssetSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {
        "item": Item, "category": ItemCategory, "vendor": Vendor,
        "warehouse": Warehouse, "location": StorageLocation,
    }
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    vendor_name = serializers.CharField(source="vendor.company_name", read_only=True, default=None)

    class Meta:
        model = Asset
        fields = [
            "id", "asset_tag", "barcode", "qr_code", "name", "item", "category",
            "category_name", "serial_number", "purchase_date", "purchase_cost",
            "vendor", "vendor_name", "warranty_until", "insurance",
            "useful_life_months", "salvage_value", "depreciation_method",
            "accounting_asset", "status", "condition", "department",
            "warehouse", "location", "assigned_room", "assigned_bed",
            "assigned_resident", "assigned_student", "assigned_staff",
            "iot_device_id", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "asset_tag", "status", "assigned_room", "assigned_bed",
            "assigned_resident", "assigned_student", "assigned_staff",
            "created_at", "updated_at",
        ]


class AssetAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetAssignment
        fields = [
            "id", "asset", "room", "bed", "resident", "student", "staff",
            "assigned_at", "returned_at", "note",
        ]
        read_only_fields = fields


class AssetLifecycleEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetLifecycleEvent
        fields = ["id", "asset", "stage", "cost", "complaint", "note", "occurred_at"]
        read_only_fields = fields


# --------------------------------------------------------------------------- #
# Action payloads (plain serializers)
# --------------------------------------------------------------------------- #
class AdjustStockSerializer(_HostelScopedRelationsMixin, serializers.Serializer):
    scoped_relations = {"warehouse": Warehouse, "location": StorageLocation}
    warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.none())
    location = serializers.PrimaryKeyRelatedField(
        queryset=StorageLocation.objects.none(), required=False, allow_null=True
    )
    target_quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class TransferStockSerializer(_HostelScopedRelationsMixin, serializers.Serializer):
    scoped_relations = {"from_warehouse": Warehouse, "to_warehouse": Warehouse}
    from_warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.none())
    to_warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.none())
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class IssueStockSerializer(_HostelScopedRelationsMixin, serializers.Serializer):
    """Issue/allocate/consume stock out to a Room/Bed and optional occupant."""

    scoped_relations = {"warehouse": Warehouse, "location": StorageLocation}
    warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.none())
    location = serializers.PrimaryKeyRelatedField(
        queryset=StorageLocation.objects.none(), required=False, allow_null=True
    )
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    movement_type = serializers.ChoiceField(
        choices=StockMovement.MovementType.choices,
        default=StockMovement.MovementType.CONSUMPTION,
    )
    room = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Room.objects.none())
    bed = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Bed.objects.none())
    resident = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Resident.objects.none())
    student = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Student.objects.none())
    reason = serializers.CharField(required=False, allow_blank=True, default="")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        hostel = getattr(request, "hostel", None)
        if hostel is None:
            return
        self.fields["room"].queryset = Room.objects.filter(hostel=hostel)
        self.fields["bed"].queryset = Bed.objects.filter(hostel=hostel)
        self.fields["resident"].queryset = Resident.objects.filter(hostel=hostel)
        self.fields["student"].queryset = Student.objects.filter(hostel=hostel)


class ReceiveGoodsLineSerializer(serializers.Serializer):
    po_line = serializers.UUIDField(required=False, allow_null=True)
    item = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    batch_number = serializers.CharField(required=False, allow_blank=True, default="")
    location = serializers.UUIDField(required=False, allow_null=True)


class ReceiveGoodsSerializer(serializers.Serializer):
    warehouse = serializers.UUIDField(required=False, allow_null=True)
    received_date = serializers.DateField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, default="")
    lines = ReceiveGoodsLineSerializer(many=True)


class AssignAssetSerializer(serializers.Serializer):
    room = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Room.objects.none())
    bed = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Bed.objects.none())
    resident = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Resident.objects.none())
    student = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Student.objects.none())
    staff = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=StaffProfile.objects.none())
    note = serializers.CharField(required=False, allow_blank=True, default="")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        hostel = getattr(request, "hostel", None)
        if hostel is None:
            return
        self.fields["room"].queryset = Room.objects.filter(hostel=hostel)
        self.fields["bed"].queryset = Bed.objects.filter(hostel=hostel)
        self.fields["resident"].queryset = Resident.objects.filter(hostel=hostel)
        self.fields["student"].queryset = Student.objects.filter(hostel=hostel)
        self.fields["staff"].queryset = StaffProfile.objects.filter(hostel=hostel)


class ChangeAssetStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Asset.Status.choices)
    note = serializers.CharField(required=False, allow_blank=True, default="")
    cost = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, default=0
    )
