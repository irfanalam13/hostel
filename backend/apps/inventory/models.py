"""Inventory & Asset Management domain models.

An ERP-style inventory layer on top of the multi-tenant core. Everything is
scoped to ``tenants.Hostel`` via ``HostelScopedModel`` (UUID pk + timestamps +
hostel FK) so no stock, purchase or asset row is ever shared between
workspaces.

Domain map:

- **Catalog & masters** — ``ItemCategory`` (self-nesting), ``Brand``,
  ``UnitOfMeasure`` and the ``Item`` master (SKU/barcode/QR, classification,
  pricing, tracking flags, reorder policy).
- **Warehousing** — ``Warehouse`` + ``StorageLocation``; ``StockLevel`` is the
  per (item, warehouse, location) source of truth for on-hand quantities, with
  ``Batch`` / ``SerialUnit`` for lot- and serial-tracked items.
- **Movements** — ``StockMovement`` is the append-only ledger of every
  quantity change; ``StockCount`` / ``StockCountLine`` reconcile physical counts.
- **Procurement** — ``Vendor``, ``PurchaseOrder`` + ``PurchaseOrderLine``, and
  ``GoodsReceipt`` + ``GoodsReceiptLine``.
- **Assets** — ``Asset`` (native lifecycle/condition/assignment) with an
  optional link to ``accounting.FixedAsset`` for depreciation, plus
  ``AssetAssignment`` and ``AssetLifecycleEvent`` history.

Numbers (SKU / PO / GRN / asset tag / movement ref) are minted per-workspace
through ``InventorySequence`` (see ``services.next_number``). Quantities are strictly
non-negative on stock levels; signed direction lives on ``StockMovement``.
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.models import HostelScopedModel, SoftDeleteModel

NON_NEGATIVE_QTY = [MinValueValidator(Decimal("0"))]
NON_NEGATIVE_AMOUNT = [MinValueValidator(Decimal("0.00"))]

# Money/quantity field shapes reused across the module.
_QTY = dict(max_digits=14, decimal_places=3, default=Decimal("0"), validators=NON_NEGATIVE_QTY)
_MONEY = dict(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=NON_NEGATIVE_AMOUNT)


def _actor_fk(related="+"):
    return models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name=related,
    )


# --------------------------------------------------------------------------- #
# Numbering
# --------------------------------------------------------------------------- #
class InventorySequence(HostelScopedModel):
    """Per-workspace monotonic counters for human-facing document numbers
    (SKU / purchase order / goods receipt / asset tag / movement ref). Rows are
    locked with ``select_for_update`` inside the issuing transaction so
    concurrent issuance can't mint duplicates."""

    key = models.CharField(max_length=32)
    next_number = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["hostel", "key"], name="uniq_inv_sequence_per_hostel"),
        ]

    def __str__(self):
        return f"{self.key} → {self.next_number}"


# --------------------------------------------------------------------------- #
# Catalog & masters
# --------------------------------------------------------------------------- #
class ItemCategory(HostelScopedModel):
    """A grouping bucket for items, unlimited depth via ``parent``. Workspaces
    get a seeded system set (Accommodation, Furniture, Electronics, ...) and can
    add their own."""

    name = models.CharField(max_length=120)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children"
    )
    description = models.CharField(max_length=255, blank=True, default="")
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "item categories"
        constraints = [
            models.UniqueConstraint(fields=["hostel", "name", "parent"], name="uniq_item_category_per_hostel"),
        ]

    def __str__(self):
        return self.name


class Brand(HostelScopedModel):
    name = models.CharField(max_length=120)
    manufacturer = models.CharField(max_length=160, blank=True, default="")
    website = models.URLField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "name"], name="uniq_brand_per_hostel"),
        ]

    def __str__(self):
        return self.name


class UnitOfMeasure(HostelScopedModel):
    """A measurement unit (piece, box, kg, litre). ``factor`` expresses the unit
    in terms of the item's base stock unit for simple conversions."""

    name = models.CharField(max_length=60)
    symbol = models.CharField(max_length=16, blank=True, default="")
    factor = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("1"))
    is_base = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "name"], name="uniq_uom_per_hostel"),
        ]

    def __str__(self):
        return self.symbol or self.name


class Item(HostelScopedModel, SoftDeleteModel):
    """The item master — the definition of a stock-keeping unit. On-hand
    quantities live on ``StockLevel`` rows, not here."""

    class ItemType(models.TextChoices):
        CONSUMABLE = "consumable", "Consumable"
        NON_CONSUMABLE = "non_consumable", "Non-Consumable"
        ASSET = "asset", "Asset"
        SERVICE = "service", "Service"
        SPARE_PART = "spare_part", "Spare Part"

    class ValuationMethod(models.TextChoices):
        WEIGHTED_AVERAGE = "weighted_average", "Weighted Average"
        FIFO = "fifo", "FIFO"
        STANDARD = "standard", "Standard Cost"

    # Identity
    item_code = models.CharField(max_length=32, db_index=True)
    sku = models.CharField(max_length=64, blank=True, default="")
    barcode = models.CharField(max_length=64, blank=True, default="")
    qr_code = models.CharField(max_length=128, blank=True, default="")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")

    # Classification
    category = models.ForeignKey(
        ItemCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="items"
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="items"
    )
    model = models.CharField(max_length=120, blank=True, default="")
    manufacturer = models.CharField(max_length=160, blank=True, default="")
    item_type = models.CharField(
        max_length=16, choices=ItemType.choices, default=ItemType.CONSUMABLE, db_index=True
    )

    # Units
    stock_uom = models.ForeignKey(
        UnitOfMeasure, on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_items"
    )
    purchase_uom = models.ForeignKey(
        UnitOfMeasure, on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase_items"
    )

    # Reorder policy
    min_stock = models.DecimalField(**_QTY)
    max_stock = models.DecimalField(**_QTY)
    reorder_level = models.DecimalField(**_QTY)
    safety_stock = models.DecimalField(**_QTY)

    # Pricing / valuation
    purchase_price = models.DecimalField(**_MONEY)
    selling_price = models.DecimalField(**_MONEY)
    average_cost = models.DecimalField(**_MONEY)
    standard_cost = models.DecimalField(**_MONEY)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    valuation_method = models.CharField(
        max_length=20, choices=ValuationMethod.choices, default=ValuationMethod.WEIGHTED_AVERAGE
    )

    # Tracking flags
    track_serial = models.BooleanField(default=False)
    track_batch = models.BooleanField(default=False)
    track_expiry = models.BooleanField(default=False)
    warranty_months = models.PositiveIntegerField(default=0)

    # Default location
    default_warehouse = models.ForeignKey(
        "Warehouse", on_delete=models.SET_NULL, null=True, blank=True, related_name="default_items"
    )

    # Extension points (RFID/NFC/IoT-ready — not wired to hardware yet)
    rfid_tag = models.CharField(max_length=128, blank=True, default="")

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "item_code"], name="uniq_item_code_per_hostel"),
        ]
        indexes = [
            models.Index(fields=["hostel", "item_type"]),
            models.Index(fields=["hostel", "is_active"]),
        ]

    def __str__(self):
        return f"{self.item_code} — {self.name}"


def _item_media_path(instance, filename):
    return f"inventory/items/{instance.item.hostel_id}/{instance.item_id}/{filename}"


class ItemImage(HostelScopedModel):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="images")
    image = models.FileField(upload_to=_item_media_path)
    caption = models.CharField(max_length=160, blank=True, default="")

    class Meta:
        ordering = ["created_at"]


class ItemDocument(HostelScopedModel):
    """Manuals, warranty files, spec sheets attached to an item."""

    class DocKind(models.TextChoices):
        MANUAL = "manual", "Manual"
        WARRANTY = "warranty", "Warranty"
        SPEC = "spec", "Specification"
        OTHER = "other", "Other"

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to=_item_media_path)
    kind = models.CharField(max_length=16, choices=DocKind.choices, default=DocKind.OTHER)
    title = models.CharField(max_length=160, blank=True, default="")

    class Meta:
        ordering = ["created_at"]


# --------------------------------------------------------------------------- #
# Warehousing
# --------------------------------------------------------------------------- #
class Warehouse(HostelScopedModel):
    class WarehouseType(models.TextChoices):
        MAIN = "main", "Main Warehouse"
        KITCHEN = "kitchen", "Kitchen"
        MAINTENANCE = "maintenance", "Maintenance"
        LAUNDRY = "laundry", "Laundry"
        OFFICE = "office", "Office"
        BRANCH = "branch", "Branch"

    name = models.CharField(max_length=160)
    warehouse_type = models.CharField(
        max_length=16, choices=WarehouseType.choices, default=WarehouseType.MAIN
    )
    capacity = models.PositiveIntegerField(default=0)
    temperature = models.CharField(max_length=40, blank=True, default="")
    security_level = models.CharField(max_length=40, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "name"], name="uniq_warehouse_per_hostel"),
        ]

    def __str__(self):
        return self.name


class StorageLocation(HostelScopedModel):
    """A bin within a warehouse (zone / rack / shelf / bin), optionally mapped
    to a physical hostel room."""

    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(max_length=120)
    zone = models.CharField(max_length=60, blank=True, default="")
    rack = models.CharField(max_length=60, blank=True, default="")
    shelf = models.CharField(max_length=60, blank=True, default="")
    bin = models.CharField(max_length=60, blank=True, default="")
    room = models.ForeignKey(
        "rooms.Room", on_delete=models.SET_NULL, null=True, blank=True, related_name="storage_locations"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["warehouse__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "warehouse", "name"], name="uniq_location_per_warehouse"
            ),
        ]

    def __str__(self):
        return f"{self.warehouse.name} / {self.name}"


class StockLevel(HostelScopedModel):
    """On-hand truth per (item, warehouse, location). Movements maintain this;
    it is never edited directly by the API."""

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="stock_levels")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stock_levels")
    location = models.ForeignKey(
        StorageLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_levels"
    )
    quantity_on_hand = models.DecimalField(**_QTY)
    quantity_reserved = models.DecimalField(**_QTY)
    quantity_allocated = models.DecimalField(**_QTY)

    class Meta:
        ordering = ["item__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "item", "warehouse", "location"],
                name="uniq_stocklevel_per_bin",
            ),
        ]
        indexes = [models.Index(fields=["hostel", "item"])]

    @property
    def quantity_available(self) -> Decimal:
        return self.quantity_on_hand - self.quantity_reserved - self.quantity_allocated

    def __str__(self):
        return f"{self.item.name} @ {self.warehouse.name}: {self.quantity_on_hand}"


class Batch(HostelScopedModel):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="batches")
    batch_number = models.CharField(max_length=64)
    expiry_date = models.DateField(null=True, blank=True)
    quantity = models.DecimalField(**_QTY)

    class Meta:
        ordering = ["expiry_date", "batch_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "item", "batch_number"], name="uniq_batch_per_item"
            ),
        ]

    def __str__(self):
        return f"{self.item.name} — {self.batch_number}"


class SerialUnit(HostelScopedModel):
    class Status(models.TextChoices):
        IN_STOCK = "in_stock", "In Stock"
        ISSUED = "issued", "Issued"
        RETURNED = "returned", "Returned"
        DAMAGED = "damaged", "Damaged"
        LOST = "lost", "Lost"

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="serial_units")
    serial_number = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.IN_STOCK)
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name="serial_units"
    )
    # Extension point (NFC-ready)
    nfc_id = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        ordering = ["serial_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "item", "serial_number"], name="uniq_serial_per_item"
            ),
        ]

    def __str__(self):
        return self.serial_number


# --------------------------------------------------------------------------- #
# Stock movements (immutable ledger)
# --------------------------------------------------------------------------- #
class StockMovement(HostelScopedModel):
    """An append-only record of one quantity change. Never edited or deleted —
    corrections are new offsetting movements. ``apply_movement`` writes these
    and updates the affected ``StockLevel`` in the same transaction."""

    class MovementType(models.TextChoices):
        PURCHASE = "purchase", "Purchase / Receipt"
        SALES = "sales", "Sale / Issue"
        TRANSFER = "transfer", "Internal Transfer"
        MAINTENANCE = "maintenance", "Maintenance Usage"
        ALLOCATION = "allocation", "Allocation"
        CONSUMPTION = "consumption", "Consumption"
        RETURN = "return", "Return"
        ADJUSTMENT = "adjustment", "Adjustment"
        DAMAGE = "damage", "Damage"
        LOST = "lost", "Lost"
        WRITE_OFF = "write_off", "Write-Off"

    class Direction(models.TextChoices):
        IN = "in", "In"
        OUT = "out", "Out"

    reference = models.CharField(max_length=32, db_index=True)
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="movements")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="movements")
    location = models.ForeignKey(
        StorageLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name="movements"
    )
    movement_type = models.CharField(max_length=16, choices=MovementType.choices, db_index=True)
    direction = models.CharField(max_length=4, choices=Direction.choices)
    quantity = models.DecimalField(**_QTY)
    unit_cost = models.DecimalField(**_MONEY)

    # Source document linkage (mirrors finance's entity_type/entity_id pattern).
    source_type = models.CharField(max_length=48, blank=True, default="")
    source_id = models.CharField(max_length=64, blank=True, default="")

    # Optional allocation targets — Room/Bed plus either occupant (all nullable).
    room = models.ForeignKey(
        "rooms.Room", on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory_movements"
    )
    bed = models.ForeignKey(
        "rooms.Bed", on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory_movements"
    )
    resident = models.ForeignKey(
        "residents.Resident", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inventory_movements",
    )
    student = models.ForeignKey(
        "students.Student", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inventory_movements",
    )
    complaint = models.ForeignKey(
        "complaints.Complaint", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inventory_movements",
    )

    reason = models.CharField(max_length=200, blank=True, default="")
    note = models.TextField(blank=True, default="")
    created_by = _actor_fk()
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(fields=["hostel", "item", "occurred_at"]),
            models.Index(fields=["hostel", "movement_type"]),
        ]

    def __str__(self):
        return f"{self.reference} {self.direction} {self.quantity} {self.item.name}"


class StockCount(HostelScopedModel):
    """A physical count / cycle-count header. Applying it generates ADJUSTMENT
    movements for every line whose counted quantity differs from the system."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    reference = models.CharField(max_length=32, db_index=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="stock_counts")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True)
    note = models.CharField(max_length=255, blank=True, default="")
    created_by = _actor_fk()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.reference


class StockCountLine(HostelScopedModel):
    stock_count = models.ForeignKey(StockCount, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="+")
    location = models.ForeignKey(
        StorageLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    system_quantity = models.DecimalField(**_QTY)
    counted_quantity = models.DecimalField(**_QTY)

    class Meta:
        ordering = ["item__name"]

    @property
    def variance(self) -> Decimal:
        return self.counted_quantity - self.system_quantity


# --------------------------------------------------------------------------- #
# Procurement
# --------------------------------------------------------------------------- #
class Vendor(HostelScopedModel, SoftDeleteModel):
    vendor_code = models.CharField(max_length=32, db_index=True)
    company_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=160, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=40, blank=True, default="")
    website = models.URLField(blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    tax_number = models.CharField(max_length=64, blank=True, default="")
    pan_vat = models.CharField(max_length=64, blank=True, default="")
    payment_terms = models.CharField(max_length=120, blank=True, default="")
    bank_details = models.JSONField(default=dict, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal("0.0"))
    is_blacklisted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company_name"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "vendor_code"], name="uniq_vendor_code_per_hostel"),
        ]

    def __str__(self):
        return self.company_name


class PurchaseOrder(HostelScopedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        ORDERED = "ordered", "Ordered"
        PARTIALLY_RECEIVED = "partially_received", "Partially Received"
        FULLY_RECEIVED = "fully_received", "Fully Received"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    po_number = models.CharField(max_length=32, db_index=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="purchase_orders")
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase_orders"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    order_date = models.DateField(default=timezone.localdate)
    expected_date = models.DateField(null=True, blank=True)

    subtotal = models.DecimalField(**_MONEY)
    tax_total = models.DecimalField(**_MONEY)
    discount_total = models.DecimalField(**_MONEY)
    total = models.DecimalField(**_MONEY)

    notes = models.TextField(blank=True, default="")
    created_by = _actor_fk()
    approved_by = _actor_fk()
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-order_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "po_number"], name="uniq_po_number_per_hostel"),
        ]
        indexes = [models.Index(fields=["hostel", "status"])]

    def __str__(self):
        return self.po_number


class PurchaseOrderLine(HostelScopedModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="po_lines")
    description = models.CharField(max_length=255, blank=True, default="")
    ordered_quantity = models.DecimalField(**_QTY)
    received_quantity = models.DecimalField(**_QTY)
    unit_price = models.DecimalField(**_MONEY)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(**_MONEY)
    line_total = models.DecimalField(**_MONEY)

    class Meta:
        ordering = ["created_at"]

    @property
    def outstanding_quantity(self) -> Decimal:
        return max(self.ordered_quantity - self.received_quantity, Decimal("0"))


class GoodsReceipt(HostelScopedModel):
    grn_number = models.CharField(max_length=32, db_index=True)
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.PROTECT, related_name="receipts"
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="receipts")
    received_date = models.DateField(default=timezone.localdate)
    received_by = _actor_fk()
    note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-received_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "grn_number"], name="uniq_grn_number_per_hostel"),
        ]

    def __str__(self):
        return self.grn_number


class GoodsReceiptLine(HostelScopedModel):
    goods_receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name="lines")
    po_line = models.ForeignKey(
        PurchaseOrderLine, on_delete=models.SET_NULL, null=True, blank=True, related_name="receipt_lines"
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="grn_lines")
    quantity = models.DecimalField(**_QTY)
    unit_cost = models.DecimalField(**_MONEY)
    batch_number = models.CharField(max_length=64, blank=True, default="")
    location = models.ForeignKey(
        StorageLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["created_at"]


# --------------------------------------------------------------------------- #
# Assets
# --------------------------------------------------------------------------- #
class Asset(HostelScopedModel, SoftDeleteModel):
    """A tracked fixed/durable asset with a native lifecycle. Optionally linked
    to ``accounting.FixedAsset`` so depreciation posts to the ledger when the
    accounting module is enabled."""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        ASSIGNED = "assigned", "Assigned"
        IN_MAINTENANCE = "in_maintenance", "In Maintenance"
        LOST = "lost", "Lost"
        DAMAGED = "damaged", "Damaged"
        RETIRED = "retired", "Retired"
        DISPOSED = "disposed", "Disposed"

    class Condition(models.TextChoices):
        NEW = "new", "New"
        GOOD = "good", "Good"
        FAIR = "fair", "Fair"
        POOR = "poor", "Poor"
        UNUSABLE = "unusable", "Unusable"

    class DepreciationMethod(models.TextChoices):
        NONE = "none", "None"
        STRAIGHT_LINE = "straight_line", "Straight Line"
        DECLINING = "declining", "Declining Balance"

    asset_tag = models.CharField(max_length=32, db_index=True)
    barcode = models.CharField(max_length=64, blank=True, default="")
    qr_code = models.CharField(max_length=128, blank=True, default="")
    name = models.CharField(max_length=200)
    item = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets"
    )
    category = models.ForeignKey(
        ItemCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets"
    )
    serial_number = models.CharField(max_length=128, blank=True, default="")

    # Acquisition
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(**_MONEY)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets"
    )
    warranty_until = models.DateField(null=True, blank=True)
    insurance = models.JSONField(default=dict, blank=True)

    # Depreciation
    useful_life_months = models.PositiveIntegerField(default=0)
    salvage_value = models.DecimalField(**_MONEY)
    depreciation_method = models.CharField(
        max_length=16, choices=DepreciationMethod.choices, default=DepreciationMethod.NONE
    )
    accounting_asset = models.ForeignKey(
        "accounting.FixedAsset", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inventory_assets",
    )

    # State
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    condition = models.CharField(max_length=16, choices=Condition.choices, default=Condition.GOOD)
    department = models.CharField(max_length=120, blank=True, default="")

    # Current location / assignment (all optional)
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets"
    )
    location = models.ForeignKey(
        StorageLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets"
    )
    assigned_room = models.ForeignKey(
        "rooms.Room", on_delete=models.SET_NULL, null=True, blank=True, related_name="assets"
    )
    assigned_bed = models.ForeignKey(
        "rooms.Bed", on_delete=models.SET_NULL, null=True, blank=True, related_name="assets"
    )
    assigned_resident = models.ForeignKey(
        "residents.Resident", on_delete=models.SET_NULL, null=True, blank=True, related_name="assets"
    )
    assigned_student = models.ForeignKey(
        "students.Student", on_delete=models.SET_NULL, null=True, blank=True, related_name="assets"
    )
    assigned_staff = models.ForeignKey(
        "staff.StaffProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="assets"
    )

    # Extension point (IoT-ready)
    iot_device_id = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "asset_tag"], name="uniq_asset_tag_per_hostel"),
        ]
        indexes = [
            models.Index(fields=["hostel", "status"]),
            models.Index(fields=["hostel", "category"]),
        ]

    def __str__(self):
        return f"{self.asset_tag} — {self.name}"


class AssetAssignment(HostelScopedModel):
    """Append-only assignment history for an asset (who/where, when returned)."""

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="assignments")
    room = models.ForeignKey("rooms.Room", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    bed = models.ForeignKey("rooms.Bed", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    resident = models.ForeignKey(
        "residents.Resident", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    student = models.ForeignKey(
        "students.Student", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    staff = models.ForeignKey(
        "staff.StaffProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    returned_at = models.DateTimeField(null=True, blank=True)
    assigned_by = _actor_fk()
    note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-assigned_at"]


class AssetLifecycleEvent(HostelScopedModel):
    """Append-only stage/status transitions and maintenance/repair records."""

    class Stage(models.TextChoices):
        REQUESTED = "requested", "Requested"
        PURCHASED = "purchased", "Purchased"
        RECEIVED = "received", "Received"
        ASSIGNED = "assigned", "Assigned"
        IN_USE = "in_use", "In Use"
        MAINTENANCE = "maintenance", "Maintenance"
        REPAIR = "repair", "Repair"
        RETURNED = "returned", "Returned"
        DISPOSED = "disposed", "Disposed"
        ARCHIVED = "archived", "Archived"

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="lifecycle_events")
    stage = models.CharField(max_length=16, choices=Stage.choices)
    cost = models.DecimalField(**_MONEY)
    complaint = models.ForeignKey(
        "complaints.Complaint", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    note = models.TextField(blank=True, default="")
    created_by = _actor_fk()
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
