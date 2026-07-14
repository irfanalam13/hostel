"""Service-layer tests: stock math, weighted-average cost, procurement
lifecycle and the opt-in ledger bridge."""
from decimal import Decimal

import pytest

from apps.inventory import services
from apps.inventory.models import (
    Asset,
    PurchaseOrder,
    PurchaseOrderLine,
    StockLevel,
    StockMovement,
)

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------------- #
# Numbering & seeding
# --------------------------------------------------------------------------- #
def test_next_number_is_monotonic_and_prefixed(hostel):
    a = services.next_number(hostel, "item")
    b = services.next_number(hostel, "item")
    assert a == "SKU-000001"
    assert b == "SKU-000002"


def test_next_number_is_per_hostel(hostel, other_hostel):
    services.next_number(hostel, "item")
    assert services.next_number(other_hostel, "item") == "SKU-000001"


def test_seed_defaults_are_idempotent(hostel):
    from apps.inventory.models import ItemCategory, UnitOfMeasure, Warehouse

    services.ensure_default_categories(hostel)
    services.ensure_default_categories(hostel)
    services.ensure_default_uom(hostel)
    services.ensure_default_uom(hostel)
    services.ensure_default_warehouse(hostel)
    assert ItemCategory.objects.filter(hostel=hostel, parent__isnull=True).count() == 9
    assert UnitOfMeasure.objects.filter(hostel=hostel).count() == len(services.DEFAULT_UOMS)
    assert Warehouse.objects.filter(hostel=hostel).count() == 1


# --------------------------------------------------------------------------- #
# Movements
# --------------------------------------------------------------------------- #
def test_inbound_movement_raises_on_hand(hostel, item, warehouse):
    services.apply_movement(
        hostel=hostel, item=item, warehouse=warehouse, quantity="5",
        movement_type=StockMovement.MovementType.PURCHASE, unit_cost="100.00",
    )
    level = StockLevel.objects.get(hostel=hostel, item=item, warehouse=warehouse)
    assert level.quantity_on_hand == Decimal("5.000")


def test_outbound_movement_lowers_on_hand(hostel, item, warehouse):
    services.apply_movement(
        hostel=hostel, item=item, warehouse=warehouse, quantity="5",
        movement_type=StockMovement.MovementType.PURCHASE,
    )
    services.apply_movement(
        hostel=hostel, item=item, warehouse=warehouse, quantity="2",
        movement_type=StockMovement.MovementType.CONSUMPTION,
    )
    assert services.item_on_hand(item) == Decimal("3.000")


def test_outbound_beyond_on_hand_raises(hostel, item, warehouse):
    with pytest.raises(ValueError):
        services.apply_movement(
            hostel=hostel, item=item, warehouse=warehouse, quantity="1",
            movement_type=StockMovement.MovementType.CONSUMPTION,
        )


def test_weighted_average_cost(hostel, item, warehouse):
    services.apply_movement(
        hostel=hostel, item=item, warehouse=warehouse, quantity="10",
        movement_type=StockMovement.MovementType.PURCHASE, unit_cost="100.00",
    )
    services.apply_movement(
        hostel=hostel, item=item, warehouse=warehouse, quantity="10",
        movement_type=StockMovement.MovementType.PURCHASE, unit_cost="200.00",
    )
    item.refresh_from_db()
    # (10*100 + 10*200) / 20 = 150
    assert item.average_cost == Decimal("150.00")


def test_transfer_moves_between_warehouses(hostel, item, warehouse):
    from apps.inventory.models import Warehouse

    wh2 = Warehouse.objects.create(hostel=hostel, name="WH2")
    services.apply_movement(
        hostel=hostel, item=item, warehouse=warehouse, quantity="10",
        movement_type=StockMovement.MovementType.PURCHASE,
    )
    services.transfer_stock(
        hostel=hostel, item=item, from_warehouse=warehouse, to_warehouse=wh2, quantity="4",
    )
    assert StockLevel.objects.get(item=item, warehouse=warehouse).quantity_on_hand == Decimal("6.000")
    assert StockLevel.objects.get(item=item, warehouse=wh2).quantity_on_hand == Decimal("4.000")


def test_adjust_stock_reconciles_to_target(hostel, item, warehouse):
    services.apply_movement(
        hostel=hostel, item=item, warehouse=warehouse, quantity="10",
        movement_type=StockMovement.MovementType.PURCHASE,
    )
    services.adjust_stock(
        hostel=hostel, item=item, warehouse=warehouse, target_quantity="7",
    )
    assert services.item_on_hand(item) == Decimal("7.000")


# --------------------------------------------------------------------------- #
# Procurement
# --------------------------------------------------------------------------- #
def _po_with_line(hostel, vendor, warehouse, item, qty="10", price="100.00"):
    po = PurchaseOrder.objects.create(
        hostel=hostel, po_number=services.next_number(hostel, "purchase_order"),
        vendor=vendor, warehouse=warehouse,
    )
    line = PurchaseOrderLine.objects.create(
        hostel=hostel, purchase_order=po, item=item,
        ordered_quantity=qty, unit_price=price,
    )
    services.recalc_po_totals(po)
    return po, line


def test_po_totals_computed(hostel, vendor, warehouse, item):
    po, _ = _po_with_line(hostel, vendor, warehouse, item, qty="10", price="100.00")
    po.refresh_from_db()
    assert po.subtotal == Decimal("1000.00")
    assert po.total == Decimal("1000.00")


def test_receive_goods_updates_stock_and_status(hostel, vendor, warehouse, item):
    po, line = _po_with_line(hostel, vendor, warehouse, item, qty="10", price="100.00")
    services.approve_po(po, actor=None)
    services.receive_goods(
        po=po, warehouse=warehouse,
        lines=[{"item": item, "po_line": line, "quantity": "10", "unit_cost": "100.00"}],
    )
    line.refresh_from_db()
    po.refresh_from_db()
    assert line.received_quantity == Decimal("10.000")
    assert po.status == PurchaseOrder.Status.FULLY_RECEIVED
    assert services.item_on_hand(item) == Decimal("10.000")


def test_partial_receipt_sets_partial_status(hostel, vendor, warehouse, item):
    po, line = _po_with_line(hostel, vendor, warehouse, item, qty="10")
    services.receive_goods(
        po=po, warehouse=warehouse,
        lines=[{"item": item, "po_line": line, "quantity": "4"}],
    )
    po.refresh_from_db()
    assert po.status == PurchaseOrder.Status.PARTIALLY_RECEIVED


# --------------------------------------------------------------------------- #
# Ledger bridge (opt-in)
# --------------------------------------------------------------------------- #
def test_receive_goods_posts_journal_when_accounting_enabled(
    hostel, vendor, warehouse, item, enable_accounting_for
):
    from django.test import override_settings

    enable_accounting_for(hostel)
    from apps.accounting.models import JournalEntry

    po, line = _po_with_line(hostel, vendor, warehouse, item, qty="5", price="100.00")
    with override_settings(ENTITLEMENTS_ENFORCED=True):
        services.receive_goods(
            po=po, warehouse=warehouse,
            lines=[{"item": item, "po_line": line, "quantity": "5", "unit_cost": "100.00"}],
        )
    journals = JournalEntry.objects.filter(hostel=hostel, status=JournalEntry.Status.POSTED)
    assert journals.exists()
    j = journals.first()
    assert j.total_debit == j.total_credit == Decimal("500.00")


def test_receive_goods_no_journal_when_accounting_disabled(hostel, vendor, warehouse, item):
    """With entitlements enforced and no accounting feature, no journal posts —
    but the stock movement must still succeed (best-effort ledger bridge)."""
    from django.test import override_settings

    from apps.accounting.models import JournalEntry

    po, line = _po_with_line(hostel, vendor, warehouse, item, qty="5", price="100.00")
    with override_settings(ENTITLEMENTS_ENFORCED=True):
        services.receive_goods(
            po=po, warehouse=warehouse,
            lines=[{"item": item, "po_line": line, "quantity": "5", "unit_cost": "100.00"}],
        )
    assert not JournalEntry.objects.filter(hostel=hostel).exists()
    assert services.item_on_hand(item) == Decimal("5.000")


# --------------------------------------------------------------------------- #
# Assets
# --------------------------------------------------------------------------- #
def test_assign_and_return_asset(hostel):
    asset = Asset.objects.create(
        hostel=hostel, asset_tag="AST-000001", name="Laptop", purchase_cost="50000.00",
    )
    from apps.rooms.models import Room

    room = Room.objects.create(hostel=hostel, room_no="101", capacity=2)
    services.assign_asset(asset=asset, room=room)
    asset.refresh_from_db()
    assert asset.status == Asset.Status.ASSIGNED
    assert asset.assigned_room_id == room.id
    assert asset.assignments.filter(returned_at__isnull=True).count() == 1

    services.return_asset(asset=asset)
    asset.refresh_from_db()
    assert asset.status == Asset.Status.AVAILABLE
    assert asset.assigned_room_id is None
    assert asset.assignments.filter(returned_at__isnull=True).count() == 0


def test_low_stock_alert_fires(hostel, item, warehouse):
    # Item reorder_level is 10; receive 5 → below reorder.
    sent = services.apply_movement(
        hostel=hostel, item=item, warehouse=warehouse, quantity="5",
        movement_type=StockMovement.MovementType.PURCHASE,
    )
    assert sent is not None
    assert services.check_and_alert_low_stock(hostel, item) is True
