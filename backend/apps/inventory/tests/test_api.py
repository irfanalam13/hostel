"""End-to-end API tests through the full auth + tenant + RBAC + feature stack."""
import pytest

pytestmark = pytest.mark.django_db

BASE = "/api/inventory"


def _data(resp):
    return resp.json()["data"]


def _results(resp):
    data = _data(resp)
    return data["results"] if isinstance(data, dict) and "results" in data else data


# --------------------------------------------------------------------------- #
# Feature gating & RBAC
# --------------------------------------------------------------------------- #
class TestGating:
    def test_feature_disabled_returns_403_when_enforced(self, auth_client, other_hostel, make_user):
        """With entitlements enforced, a hostel lacking the inventory feature is
        denied (the autouse fixture only enables it for the primary hostel)."""
        from django.test import override_settings

        user = make_user(role="MANAGER", hostel=other_hostel)
        client = auth_client(user, other_hostel)
        with override_settings(ENTITLEMENTS_ENFORCED=True):
            resp = client.get(f"{BASE}/items/")
        assert resp.status_code == 403

    def test_resident_role_denied(self, auth_client, resident_user, hostel):
        client = auth_client(resident_user, hostel)
        resp = client.get(f"{BASE}/items/")
        assert resp.status_code == 403

    def test_manager_can_list(self, manager_client):
        resp = manager_client.get(f"{BASE}/items/")
        assert resp.status_code == 200


# --------------------------------------------------------------------------- #
# Items
# --------------------------------------------------------------------------- #
class TestItems:
    def test_create_mints_item_code(self, manager_client):
        resp = manager_client.post(
            f"{BASE}/items/", {"name": "Pillow", "reorder_level": "5"}, format="json"
        )
        assert resp.status_code == 201, resp.content
        assert _data(resp)["item_code"].startswith("SKU-")

    def test_list_excludes_archived(self, manager_client, item):
        manager_client.delete(f"{BASE}/items/{item.id}/")
        rows = _results(manager_client.get(f"{BASE}/items/"))
        assert all(r["id"] != str(item.id) for r in rows)

    def test_adjust_stock_action(self, manager_client, item, warehouse):
        resp = manager_client.post(
            f"{BASE}/items/{item.id}/adjust-stock/",
            {"warehouse": str(warehouse.id), "target_quantity": "8"}, format="json",
        )
        assert resp.status_code == 200, resp.content
        detail = manager_client.get(f"{BASE}/items/{item.id}/")
        assert _data(detail)["on_hand"] == "8.000"


# --------------------------------------------------------------------------- #
# Categories seeding
# --------------------------------------------------------------------------- #
class TestCategories:
    def test_defaults_seeded_on_list(self, manager_client):
        rows = _results(manager_client.get(f"{BASE}/categories/"))
        names = {r["name"] for r in rows}
        assert "Accommodation" in names and "Electronics" in names

    def test_system_category_cannot_be_deleted(self, manager_client):
        rows = _results(manager_client.get(f"{BASE}/categories/"))
        system = next(r for r in rows if r["is_system"])
        resp = manager_client.delete(f"{BASE}/categories/{system['id']}/")
        assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# Procurement workflow
# --------------------------------------------------------------------------- #
class TestPurchaseWorkflow:
    def test_full_po_to_grn_flow(self, manager_client, vendor, warehouse, item):
        create = manager_client.post(
            f"{BASE}/purchase-orders/",
            {
                "vendor": str(vendor.id), "warehouse": str(warehouse.id),
                "lines": [{"item": str(item.id), "ordered_quantity": "10", "unit_price": "100.00"}],
            },
            format="json",
        )
        assert create.status_code == 201, create.content
        po = _data(create)
        assert po["po_number"].startswith("PO-")
        assert po["total"] == "1000.00"
        po_id = po["id"]
        po_line_id = po["lines"][0]["id"]

        assert manager_client.post(f"{BASE}/purchase-orders/{po_id}/approve/").status_code == 200

        receive = manager_client.post(
            f"{BASE}/purchase-orders/{po_id}/receive/",
            {"lines": [{"item": str(item.id), "po_line": po_line_id, "quantity": "10", "unit_cost": "100.00"}]},
            format="json",
        )
        assert receive.status_code == 201, receive.content
        assert _data(receive)["grn_number"].startswith("GRN-")

        detail = manager_client.get(f"{BASE}/purchase-orders/{po_id}/")
        assert _data(detail)["status"] == "fully_received"
        item_detail = manager_client.get(f"{BASE}/items/{item.id}/")
        assert _data(item_detail)["on_hand"] == "10.000"


# --------------------------------------------------------------------------- #
# Assets
# --------------------------------------------------------------------------- #
class TestAssets:
    def test_create_and_change_status(self, manager_client, vendor):
        create = manager_client.post(
            f"{BASE}/assets/",
            {"name": "Projector", "purchase_cost": "30000.00", "vendor": str(vendor.id)},
            format="json",
        )
        assert create.status_code == 201, create.content
        asset = _data(create)
        assert asset["asset_tag"].startswith("AST-")

        resp = manager_client.post(
            f"{BASE}/assets/{asset['id']}/change-status/",
            {"status": "in_maintenance", "note": "Bulb"}, format="json",
        )
        assert resp.status_code == 200
        assert _data(resp)["status"] == "in_maintenance"

    def test_history_endpoint(self, manager_client):
        create = manager_client.post(
            f"{BASE}/assets/", {"name": "Fan", "purchase_cost": "2000.00"}, format="json"
        )
        aid = _data(create)["id"]
        manager_client.post(
            f"{BASE}/assets/{aid}/change-status/", {"status": "damaged"}, format="json"
        )
        hist = manager_client.get(f"{BASE}/assets/{aid}/history/")
        assert hist.status_code == 200
        assert len(_data(hist)) >= 1


# --------------------------------------------------------------------------- #
# Dashboard & reports
# --------------------------------------------------------------------------- #
class TestDashboardReports:
    def test_dashboard_summary(self, manager_client, item):
        resp = manager_client.get(f"{BASE}/dashboard/summary/")
        assert resp.status_code == 200
        assert "totals" in _data(resp)

    def test_report_csv_export(self, manager_client):
        resp = manager_client.get(f"{BASE}/reports/export/?type=stock-summary&fmt=csv")
        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/csv")
