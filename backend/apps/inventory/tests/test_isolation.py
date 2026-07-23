"""Cross-tenant isolation: one workspace can never see or touch another's
inventory rows."""
import pytest

pytestmark = pytest.mark.django_db

BASE = "/api/inventory"


def _results(resp):
    data = resp.json()["data"]
    return data["results"] if isinstance(data, dict) and "results" in data else data


@pytest.fixture
def other_item(other_hostel):
    from apps.inventory.models import Item

    return Item.objects.create(
        hostel=other_hostel, item_code="SKU-000001", name="Foreign Item",
    )


class TestIsolation:
    def test_item_list_scoped_to_hostel(self, manager_client, item, other_item):
        rows = _results(manager_client.get(f"{BASE}/items/"))
        ids = {r["id"] for r in rows}
        assert str(item.id) in ids
        assert str(other_item.id) not in ids

    def test_cannot_retrieve_foreign_item(self, manager_client, other_item):
        resp = manager_client.get(f"{BASE}/items/{other_item.id}/")
        assert resp.status_code == 404

    def test_cannot_delete_foreign_item(self, manager_client, other_item):
        resp = manager_client.delete(f"{BASE}/items/{other_item.id}/")
        assert resp.status_code == 404

    def test_vendor_scoped(self, manager_client, vendor, other_hostel):
        from apps.inventory.models import Vendor

        foreign = Vendor.objects.create(
            hostel=other_hostel, vendor_code="VEN-000001", company_name="Foreign Co"
        )
        rows = _results(manager_client.get(f"{BASE}/vendors/"))
        ids = {r["id"] for r in rows}
        assert str(vendor.id) in ids
        assert str(foreign.id) not in ids
