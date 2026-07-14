"""Inventory domain services — the single place stock math, procurement
lifecycle transitions, asset operations and ledger/notification side effects
happen.

Views validate + authorize; these functions mutate stock levels, mint document
numbers and post to accounting/finance, all inside DB transactions so
concurrent receipts/issues can't corrupt on-hand quantities. Ledger posting and
low-stock alerts are best-effort — a failure there never rolls back the stock
mutation that triggered it.
"""
import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import (
    Asset,
    AssetAssignment,
    AssetLifecycleEvent,
    Batch,
    GoodsReceipt,
    GoodsReceiptLine,
    InventorySequence,
    Item,
    ItemCategory,
    PurchaseOrder,
    PurchaseOrderLine,
    StockCount,
    StockLevel,
    StockMovement,
    UnitOfMeasure,
    Warehouse,
)

logger = logging.getLogger(__name__)

ZERO = Decimal("0")
MONEY = Decimal("0.01")
QTY = Decimal("0.001")

# Movement types that increase on-hand stock.
_INBOUND_TYPES = {
    StockMovement.MovementType.PURCHASE,
    StockMovement.MovementType.RETURN,
}


# --------------------------------------------------------------------------- #
# Numbering
# --------------------------------------------------------------------------- #
_PREFIXES = {
    "item": "SKU",
    "purchase_order": "PO",
    "goods_receipt": "GRN",
    "asset": "AST",
    "movement": "MOV",
    "stock_count": "SC",
    "vendor": "VEN",
}


def next_number(hostel, key: str) -> str:
    """Mint the next human-facing number for a document key, atomically.

    The per-(hostel, key) counter row is locked for the caller's transaction so
    two concurrent documents can't share a number.
    """
    prefix = _PREFIXES.get(key, key[:3].upper())
    seq, _ = InventorySequence.objects.get_or_create(hostel=hostel, key=key)
    seq = InventorySequence.objects.select_for_update().get(pk=seq.pk)
    number = seq.next_number
    seq.next_number = number + 1
    seq.save(update_fields=["next_number", "updated_at"])
    return f"{prefix}-{number:06d}"


# --------------------------------------------------------------------------- #
# Seeding
# --------------------------------------------------------------------------- #
# (category, [subcategories]) — the seeded system taxonomy.
DEFAULT_CATEGORIES = {
    "Accommodation": ["Beds", "Mattresses", "Pillows", "Blankets", "Bedsheets", "Towels"],
    "Furniture": ["Tables", "Chairs", "Wardrobes", "Cabinets", "Desks"],
    "Electronics": ["Computers", "Laptops", "Printers", "Routers", "CCTV", "TVs", "Projectors"],
    "Kitchen": ["Refrigerator", "Stove", "Gas Cylinder", "Microwave", "Utensils", "Water Purifier"],
    "Cleaning": ["Detergent", "Mop", "Bucket", "Vacuum Cleaner", "Cleaning Chemicals"],
    "Maintenance": ["Tools", "Paint", "Pipes", "Electrical Equipment", "Spare Parts"],
    "Office": ["Printer Paper", "Stationery", "Files", "Ink"],
    "Medical": ["First Aid Kits", "Medicines", "Safety Equipment"],
    "Laundry": ["Washing Machines", "Dryers", "Laundry Supplies"],
}

# (name, symbol, factor, is_base)
DEFAULT_UOMS = [
    ("Piece", "pc", Decimal("1"), True),
    ("Box", "box", Decimal("1"), False),
    ("Pack", "pack", Decimal("1"), False),
    ("Dozen", "dz", Decimal("12"), False),
    ("Kilogram", "kg", Decimal("1"), False),
    ("Gram", "g", Decimal("0.001"), False),
    ("Litre", "L", Decimal("1"), False),
    ("Set", "set", Decimal("1"), False),
]


def ensure_default_categories(hostel) -> None:
    """Idempotently seed the system category taxonomy for a workspace."""
    for parent_name, children in DEFAULT_CATEGORIES.items():
        parent, _ = ItemCategory.objects.get_or_create(
            hostel=hostel, name=parent_name, parent=None,
            defaults={"is_system": True},
        )
        for child in children:
            ItemCategory.objects.get_or_create(
                hostel=hostel, name=child, parent=parent,
                defaults={"is_system": True},
            )


def ensure_default_uom(hostel) -> None:
    for name, symbol, factor, is_base in DEFAULT_UOMS:
        UnitOfMeasure.objects.get_or_create(
            hostel=hostel, name=name,
            defaults={"symbol": symbol, "factor": factor, "is_base": is_base, "is_system": True},
        )


def ensure_default_warehouse(hostel) -> Warehouse:
    warehouse, _ = Warehouse.objects.get_or_create(
        hostel=hostel, name="Main Warehouse",
        defaults={"warehouse_type": Warehouse.WarehouseType.MAIN, "is_default": True},
    )
    return warehouse


def default_warehouse(hostel) -> Warehouse:
    """The tenant's default warehouse, seeding one if none exists."""
    wh = Warehouse.objects.filter(hostel=hostel, is_default=True).first()
    return wh or ensure_default_warehouse(hostel)


# --------------------------------------------------------------------------- #
# Stock movement engine
# --------------------------------------------------------------------------- #
def _get_stock_level(hostel, item, warehouse, location):
    level, _ = StockLevel.objects.select_for_update().get_or_create(
        hostel=hostel, item=item, warehouse=warehouse, location=location,
    )
    return level


def _recalc_average_cost(item: Item, added_qty: Decimal, unit_cost: Decimal) -> None:
    """Weighted-average cost roll-forward on an inbound movement.

    Called after the ``StockLevel`` is updated, so the aggregate already
    includes ``added_qty``; the previous quantity is derived by subtracting it.
    """
    if added_qty <= 0 or unit_cost <= 0:
        return
    from django.db.models import Sum

    total_qty = StockLevel.objects.filter(hostel=item.hostel, item=item).aggregate(
        s=Sum("quantity_on_hand")
    )["s"] or ZERO
    prev_qty = total_qty - added_qty
    prev_value = (item.average_cost or ZERO) * prev_qty
    new_value = prev_value + (unit_cost * added_qty)
    if total_qty > 0:
        item.average_cost = (new_value / total_qty).quantize(MONEY)
        item.save(update_fields=["average_cost", "updated_at"])


@transaction.atomic
def apply_movement(
    *, hostel, item, warehouse, quantity, movement_type, direction=None,
    location=None, unit_cost=None, actor=None, reason="", note="",
    source_type="", source_id="", occurred_at=None,
    room=None, bed=None, resident=None, student=None, complaint=None,
    alert=True,
) -> StockMovement:
    """Record one stock movement and update the affected ``StockLevel`` in the
    same transaction. Direction is inferred from the movement type when not
    given. Raises ``ValueError`` on an outbound move that would go negative.
    """
    quantity = Decimal(str(quantity)).quantize(QTY)
    if quantity <= 0:
        raise ValueError("Movement quantity must be positive.")

    if direction is None:
        direction = (
            StockMovement.Direction.IN
            if movement_type in _INBOUND_TYPES
            else StockMovement.Direction.OUT
        )
    if unit_cost is None:
        unit_cost = item.average_cost or item.purchase_price or Decimal("0.00")
    unit_cost = Decimal(str(unit_cost)).quantize(MONEY)

    level = _get_stock_level(hostel, item, warehouse, location)
    if direction == StockMovement.Direction.IN:
        level.quantity_on_hand = level.quantity_on_hand + quantity
    else:
        if level.quantity_on_hand < quantity:
            raise ValueError(
                f"Insufficient stock for {item.name} at {warehouse.name}: "
                f"have {level.quantity_on_hand}, need {quantity}."
            )
        level.quantity_on_hand = level.quantity_on_hand - quantity
    level.save(update_fields=["quantity_on_hand", "updated_at"])

    movement = StockMovement.objects.create(
        hostel=hostel,
        reference=next_number(hostel, "movement"),
        item=item,
        warehouse=warehouse,
        location=location,
        movement_type=movement_type,
        direction=direction,
        quantity=quantity,
        unit_cost=unit_cost,
        source_type=source_type,
        source_id=str(source_id or ""),
        reason=reason,
        note=note,
        room=room,
        bed=bed,
        resident=resident,
        student=student,
        complaint=complaint,
        created_by=actor,
        occurred_at=occurred_at or timezone.now(),
    )

    if direction == StockMovement.Direction.IN:
        _recalc_average_cost(item, quantity, unit_cost)

    if alert:
        check_and_alert_low_stock(hostel, item, actor=actor)
    return movement


def item_on_hand(item) -> Decimal:
    from django.db.models import Sum

    return (
        StockLevel.objects.filter(hostel=item.hostel, item=item).aggregate(
            s=Sum("quantity_on_hand")
        )["s"]
        or ZERO
    )


# --------------------------------------------------------------------------- #
# Higher-level stock operations
# --------------------------------------------------------------------------- #
@transaction.atomic
def transfer_stock(*, hostel, item, from_warehouse, to_warehouse, quantity, actor=None,
                   from_location=None, to_location=None, note=""):
    """Move stock between warehouses/locations as a paired OUT + IN movement."""
    out = apply_movement(
        hostel=hostel, item=item, warehouse=from_warehouse, location=from_location,
        quantity=quantity, movement_type=StockMovement.MovementType.TRANSFER,
        direction=StockMovement.Direction.OUT, actor=actor, note=note, alert=False,
    )
    into = apply_movement(
        hostel=hostel, item=item, warehouse=to_warehouse, location=to_location,
        quantity=quantity, movement_type=StockMovement.MovementType.TRANSFER,
        direction=StockMovement.Direction.IN, actor=actor, note=note,
        source_type="inventory.stockmovement", source_id=out.id, alert=False,
    )
    return out, into


@transaction.atomic
def adjust_stock(*, hostel, item, warehouse, target_quantity, actor=None, location=None, reason=""):
    """Reconcile on-hand to a counted target via a single ADJUSTMENT movement."""
    level = _get_stock_level(hostel, item, warehouse, location)
    target = Decimal(str(target_quantity)).quantize(QTY)
    delta = target - level.quantity_on_hand
    if delta == 0:
        return None
    direction = StockMovement.Direction.IN if delta > 0 else StockMovement.Direction.OUT
    return apply_movement(
        hostel=hostel, item=item, warehouse=warehouse, location=location,
        quantity=abs(delta), movement_type=StockMovement.MovementType.ADJUSTMENT,
        direction=direction, actor=actor, reason=reason or "Stock adjustment",
    )


@transaction.atomic
def complete_stock_count(count: StockCount, *, actor=None):
    """Apply a physical count: generate ADJUSTMENT movements for variances."""
    for line in count.lines.select_related("item"):
        if line.variance != 0:
            adjust_stock(
                hostel=count.hostel, item=line.item, warehouse=count.warehouse,
                location=line.location, target_quantity=line.counted_quantity,
                actor=actor, reason=f"Cycle count {count.reference}",
            )
    count.status = StockCount.Status.COMPLETED
    count.completed_at = timezone.now()
    count.save(update_fields=["status", "completed_at", "updated_at"])
    return count


# --------------------------------------------------------------------------- #
# Procurement lifecycle
# --------------------------------------------------------------------------- #
def recalc_po_totals(po: PurchaseOrder, *, save=True) -> PurchaseOrder:
    subtotal = tax_total = discount_total = Decimal("0.00")
    for line in po.lines.all():
        gross = (line.ordered_quantity * line.unit_price).quantize(MONEY)
        tax = (gross * line.tax_rate / Decimal("100")).quantize(MONEY)
        line.line_total = (gross + tax - line.discount).quantize(MONEY)
        line.save(update_fields=["line_total", "updated_at"])
        subtotal += gross
        tax_total += tax
        discount_total += line.discount
    po.subtotal = subtotal.quantize(MONEY)
    po.tax_total = tax_total.quantize(MONEY)
    po.discount_total = discount_total.quantize(MONEY)
    po.total = (subtotal + tax_total - discount_total).quantize(MONEY)
    if save:
        po.save(update_fields=["subtotal", "tax_total", "discount_total", "total", "updated_at"])
    return po


def submit_po(po: PurchaseOrder) -> PurchaseOrder:
    po.status = PurchaseOrder.Status.PENDING_APPROVAL
    po.save(update_fields=["status", "updated_at"])
    return po


def approve_po(po: PurchaseOrder, *, actor) -> PurchaseOrder:
    po.status = PurchaseOrder.Status.APPROVED
    po.approved_by = actor
    po.approved_at = timezone.now()
    po.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    return po


def cancel_po(po: PurchaseOrder) -> PurchaseOrder:
    po.status = PurchaseOrder.Status.CANCELLED
    po.save(update_fields=["status", "updated_at"])
    return po


@transaction.atomic
def receive_goods(*, po: PurchaseOrder, warehouse, lines, actor=None, received_date=None, note=""):
    """Create a goods receipt against a PO: layer stock in, update received
    quantities + PO status, and best-effort post the purchase to the ledger.

    ``lines``: dicts of ``po_line / item / quantity / unit_cost / batch_number /
    location``.
    """
    grn = GoodsReceipt.objects.create(
        hostel=po.hostel,
        grn_number=next_number(po.hostel, "goods_receipt"),
        purchase_order=po,
        warehouse=warehouse,
        received_date=received_date or timezone.localdate(),
        received_by=actor,
        note=note,
    )
    total_value = Decimal("0.00")
    for row in lines:
        item = row["item"]
        qty = Decimal(str(row["quantity"])).quantize(QTY)
        if qty <= 0:
            continue
        unit_cost = Decimal(str(row.get("unit_cost") or item.purchase_price or 0)).quantize(MONEY)
        location = row.get("location")
        GoodsReceiptLine.objects.create(
            hostel=po.hostel, goods_receipt=grn, po_line=row.get("po_line"), item=item,
            quantity=qty, unit_cost=unit_cost, batch_number=row.get("batch_number", ""),
            location=location,
        )
        apply_movement(
            hostel=po.hostel, item=item, warehouse=warehouse, location=location,
            quantity=qty, movement_type=StockMovement.MovementType.PURCHASE,
            unit_cost=unit_cost, actor=actor, source_type="inventory.goodsreceipt",
            source_id=grn.id, reason=f"GRN {grn.grn_number}",
        )
        po_line = row.get("po_line")
        if po_line is not None:
            po_line.received_quantity = (po_line.received_quantity + qty).quantize(QTY)
            po_line.save(update_fields=["received_quantity", "updated_at"])
        if row.get("batch_number") and item.track_batch:
            batch, _ = Batch.objects.get_or_create(
                hostel=po.hostel, item=item, batch_number=row["batch_number"],
            )
            batch.quantity = (batch.quantity + qty).quantize(QTY)
            batch.save(update_fields=["quantity", "updated_at"])
        total_value += (unit_cost * qty)

    _refresh_po_receipt_status(po)
    post_inventory_ledger(
        po.hostel, event="purchase", amount=total_value.quantize(MONEY), actor=actor,
        memo=f"Goods receipt {grn.grn_number}", source_type="inventory.goodsreceipt", source_id=grn.id,
    )
    return grn


def _refresh_po_receipt_status(po: PurchaseOrder) -> None:
    # Query lines fresh — the view may have prefetched them, which would return
    # stale received_quantity values cached before this receipt was applied.
    lines = list(PurchaseOrderLine.objects.filter(hostel=po.hostel, purchase_order=po))
    if lines and all(line.received_quantity >= line.ordered_quantity for line in lines):
        po.status = PurchaseOrder.Status.FULLY_RECEIVED
    elif any(line.received_quantity > 0 for line in lines):
        po.status = PurchaseOrder.Status.PARTIALLY_RECEIVED
    po.save(update_fields=["status", "updated_at"])


# --------------------------------------------------------------------------- #
# Asset operations
# --------------------------------------------------------------------------- #
@transaction.atomic
def assign_asset(*, asset: Asset, actor=None, room=None, bed=None, resident=None,
                 student=None, staff=None, note=""):
    """Assign an asset to a target, closing any open assignment first."""
    asset.assignments.filter(returned_at__isnull=True).update(returned_at=timezone.now())
    AssetAssignment.objects.create(
        hostel=asset.hostel, asset=asset, room=room, bed=bed, resident=resident,
        student=student, staff=staff, assigned_by=actor, note=note,
    )
    asset.assigned_room = room
    asset.assigned_bed = bed
    asset.assigned_resident = resident
    asset.assigned_student = student
    asset.assigned_staff = staff
    asset.status = Asset.Status.ASSIGNED
    asset.save(update_fields=[
        "assigned_room", "assigned_bed", "assigned_resident", "assigned_student",
        "assigned_staff", "status", "updated_at",
    ])
    _log_asset_event(asset, AssetLifecycleEvent.Stage.ASSIGNED, actor=actor, note=note)
    return asset


@transaction.atomic
def return_asset(*, asset: Asset, actor=None, note=""):
    asset.assignments.filter(returned_at__isnull=True).update(returned_at=timezone.now())
    asset.assigned_room = None
    asset.assigned_bed = None
    asset.assigned_resident = None
    asset.assigned_student = None
    asset.assigned_staff = None
    asset.status = Asset.Status.AVAILABLE
    asset.save(update_fields=[
        "assigned_room", "assigned_bed", "assigned_resident", "assigned_student",
        "assigned_staff", "status", "updated_at",
    ])
    _log_asset_event(asset, AssetLifecycleEvent.Stage.RETURNED, actor=actor, note=note)
    return asset


@transaction.atomic
def change_asset_status(*, asset: Asset, status, actor=None, note="", cost=Decimal("0.00")):
    asset.status = status
    asset.save(update_fields=["status", "updated_at"])
    stage_map = {
        Asset.Status.IN_MAINTENANCE: AssetLifecycleEvent.Stage.MAINTENANCE,
        Asset.Status.DISPOSED: AssetLifecycleEvent.Stage.DISPOSED,
        Asset.Status.RETIRED: AssetLifecycleEvent.Stage.ARCHIVED,
    }
    _log_asset_event(
        asset, stage_map.get(status, AssetLifecycleEvent.Stage.IN_USE),
        actor=actor, note=note, cost=cost,
    )
    if status in (Asset.Status.DISPOSED, Asset.Status.RETIRED):
        post_inventory_ledger(
            asset.hostel, event="write_off", amount=asset.purchase_cost, actor=actor,
            memo=f"Asset {asset.asset_tag} {status}", source_type="inventory.asset",
            source_id=asset.id,
        )
    return asset


def _log_asset_event(asset, stage, *, actor=None, note="", cost=Decimal("0.00")):
    AssetLifecycleEvent.objects.create(
        hostel=asset.hostel, asset=asset, stage=stage, cost=cost, note=note, created_by=actor,
    )


def run_asset_depreciation(*, asset: Asset, actor=None, on_date=None):
    """Post one period of depreciation via the accounting engine when the asset
    is linked to a ``FixedAsset`` and accounting is enabled. No-op otherwise."""
    if asset.accounting_asset_id is None:
        raise ValueError("Asset is not linked to an accounting fixed asset.")
    if not _accounting_enabled(asset.hostel):
        raise ValueError("Accounting module is not enabled for this workspace.")
    from apps.accounting.services import run_depreciation

    return run_depreciation(
        hostel=asset.hostel, actor=actor, asset=asset.accounting_asset, on_date=on_date
    )


# --------------------------------------------------------------------------- #
# Ledger bridge (opt-in, best-effort)
# --------------------------------------------------------------------------- #
def _accounting_enabled(hostel) -> bool:
    try:
        from apps.subscriptions.entitlements import Entitlements

        return Entitlements(hostel).can_use("accounting")
    except Exception:
        return False


# Ledger routing per inventory event: (debit_code, credit_code).
_LEDGER_ROUTING = {
    "purchase": ("1150", "2110"),     # Dr Inventory, Cr Accounts Payable
    "write_off": ("5900", "1150"),    # Dr Misc Expense, Cr Inventory
}


def post_inventory_ledger(hostel, *, event, amount, actor=None, memo="",
                          source_type="", source_id=""):
    """Best-effort double-entry + finance ledger post for an inventory event.

    Only posts to accounting when the module is enabled; always attempts a
    lightweight finance ``LedgerTransaction`` for the cash/expense view. Any
    failure is swallowed and logged so it can never roll back the stock
    mutation that called it.
    """
    amount = Decimal(str(amount or 0)).quantize(MONEY)
    if amount <= 0:
        return

    # 1) Double-entry journal (accounting) — opt-in.
    if _accounting_enabled(hostel):
        try:
            from apps.accounting.models import JournalEntry
            from apps.accounting.services import create_journal, get_anchor_account

            debit_code, credit_code = _LEDGER_ROUTING.get(event, (None, None))
            debit_acc = get_anchor_account(hostel, debit_code) if debit_code else None
            credit_acc = get_anchor_account(hostel, credit_code) if credit_code else None
            if debit_acc and credit_acc:
                create_journal(
                    hostel=hostel, actor=actor,
                    lines=[
                        {"account": debit_acc, "debit": amount, "credit": Decimal("0.00"), "description": memo},
                        {"account": credit_acc, "debit": Decimal("0.00"), "credit": amount, "description": memo},
                    ],
                    status=JournalEntry.Status.POSTED,
                    journal_type=JournalEntry.JournalType.AUTOMATIC,
                    description=memo or f"Inventory {event}",
                )
        except Exception:  # accounting must never break a stock mutation
            logger.warning("Inventory ledger (accounting) post failed for %s", event, exc_info=True)

    # 2) Lightweight finance ledger transaction (cash-flow view) — best effort.
    try:
        from apps.finance.models import LedgerTransaction, PaymentMethod
        from apps.finance.services import post_transaction

        direction = (
            LedgerTransaction.Direction.OUT
            if event in ("purchase", "write_off")
            else LedgerTransaction.Direction.IN
        )
        post_transaction(
            hostel=hostel, direction=direction, category=f"inventory:{event}",
            amount=amount, method=PaymentMethod.OTHER,
            entity_type=source_type or "inventory.event", entity_id=source_id or event,
            memo=memo,
        )
    except Exception:
        logger.warning("Inventory ledger (finance) post failed for %s", event, exc_info=True)


# --------------------------------------------------------------------------- #
# Alerts
# --------------------------------------------------------------------------- #
def check_and_alert_low_stock(hostel, item: Item, *, actor=None) -> bool:
    """Notify managers when an item's total on-hand falls to/below its reorder
    level. Best-effort — never raises. Returns True when an alert was sent."""
    reorder = Decimal(str(item.reorder_level or 0))
    if reorder <= 0:
        return False
    on_hand = item_on_hand(item)
    if on_hand > reorder:
        return False
    try:
        from apps.notifications.models import AudienceType
        from apps.notifications.services import create_notification

        out_of_stock = on_hand <= 0
        create_notification(
            hostel=hostel,
            title=f"{'Out of stock' if out_of_stock else 'Low stock'}: {item.name}",
            body=(
                f"{item.name} is out of stock." if out_of_stock
                else f"Only {on_hand} left (reorder level {reorder})."
            ),
            category="GENERAL",
            priority="HIGH" if out_of_stock else "NORMAL",
            url="/inventory/items",
            audience=AudienceType.ROLE,
            target_roles=["MANAGER", "ADMIN", "OWNER"],
            created_by=actor,
        )
        return True
    except Exception:  # alerts must never break a stock mutation
        logger.warning("Low-stock alert failed for item %s", item.id, exc_info=True)
        return False


# --------------------------------------------------------------------------- #
# Forecasting (AI-ready extension point)
# --------------------------------------------------------------------------- #
def forecast_consumption(item: Item, *, months: int = 3) -> dict:
    """Return a simple historical-average consumption forecast for an item.

    A deterministic baseline the future AI layer can replace — averages OUT
    movements over the trailing window and projects a reorder suggestion.
    """
    from datetime import timedelta

    from django.db.models import Sum

    since = timezone.now() - timedelta(days=30 * max(months, 1))
    consumed = (
        StockMovement.objects.filter(
            hostel=item.hostel, item=item,
            direction=StockMovement.Direction.OUT, occurred_at__gte=since,
        ).aggregate(s=Sum("quantity"))["s"]
        or ZERO
    )
    monthly = (consumed / Decimal(max(months, 1))).quantize(QTY)
    on_hand = item_on_hand(item)
    return {
        "item_id": str(item.id),
        "window_months": months,
        "total_consumed": str(consumed),
        "monthly_average": str(monthly),
        "on_hand": str(on_hand),
        "suggested_reorder": str(max(monthly - on_hand, ZERO).quantize(QTY)),
    }
