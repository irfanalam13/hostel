"""Inventory test fixtures.

The ``inventory`` feature is default-disabled in the catalog (enterprise
gating), so tests must enable it for the workspace under test — mirroring a plan
that includes inventory.
"""
import pytest


def _enable_feature(hostel, key):
    from apps.subscriptions.models import Feature, FeatureOverride

    feature = Feature.objects.filter(key=key).first()
    if feature is not None:
        FeatureOverride.objects.get_or_create(
            hostel=hostel, feature=feature, defaults={"is_enabled": True}
        )


@pytest.fixture(autouse=True)
def enable_inventory(db, hostel):
    """Grant the ``inventory`` feature to the primary test hostel."""
    _enable_feature(hostel, "inventory")
    yield


@pytest.fixture
def enable_accounting_for(db):
    """Callable to enable accounting for a given hostel (for ledger-bridge tests)."""

    def _enable(hostel):
        _enable_feature(hostel, "accounting")

    return _enable


@pytest.fixture
def manager_client(auth_client, manager, hostel):
    return auth_client(manager, hostel)


@pytest.fixture
def category(hostel):
    from apps.inventory.models import ItemCategory

    return ItemCategory.objects.create(hostel=hostel, name="Test Cat")


@pytest.fixture
def warehouse(hostel):
    from apps.inventory.models import Warehouse

    return Warehouse.objects.create(hostel=hostel, name="WH1", is_default=True)


@pytest.fixture
def item(hostel):
    from apps.inventory.models import Item

    return Item.objects.create(
        hostel=hostel, item_code="SKU-000001", name="Bedsheet",
        reorder_level="10", purchase_price="100.00",
    )


@pytest.fixture
def vendor(hostel):
    from apps.inventory.models import Vendor

    return Vendor.objects.create(hostel=hostel, vendor_code="VEN-000001", company_name="Acme")
