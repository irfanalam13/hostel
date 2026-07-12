"""Finance API tests: end-to-end flows through the full auth + tenant +
RBAC stack (invoicing, collection, expenses, income, refunds, dashboard,
reports, exports) plus permission enforcement per role."""
from decimal import Decimal

import pytest

from apps.finance.models import (
    Income,
    Invoice,
    LedgerTransaction,
    PaymentRecord,
)

pytestmark = pytest.mark.django_db

BASE = "/api/finance"


def _data(resp):
    return resp.json()["data"]


@pytest.fixture
def accountant_client(auth_client, accountant, hostel):
    return auth_client(accountant, hostel)


@pytest.fixture
def warden_client(auth_client, warden, hostel):
    return auth_client(warden, hostel)


@pytest.fixture
def invoice_payload(resident):
    return {
        "resident": str(resident.id),
        "due_date": "2026-08-01",
        "lines": [
            {"description": "Hostel fee", "quantity": "1", "unit_price": "5000.00"},
            {"description": "Mess fee", "quantity": "1", "unit_price": "2000.00", "tax_rate": "13"},
        ],
    }


class TestInvoiceApi:
    def test_create_computes_totals_and_number(self, accountant_client, invoice_payload):
        resp = accountant_client.post(f"{BASE}/invoices/", invoice_payload, format="json")
        assert resp.status_code == 201, resp.content
        data = _data(resp)
        assert data["number"].startswith("INV-")
        assert data["subtotal"] == "7000.00"
        assert data["tax_total"] == "260.00"
        assert data["total"] == "7260.00"
        assert data["status"] == "pending"
        assert len(data["lines"]) == 2

    def test_draft_then_issue(self, accountant_client, invoice_payload):
        invoice_payload["as_draft"] = True
        resp = accountant_client.post(f"{BASE}/invoices/", invoice_payload, format="json")
        data = _data(resp)
        assert data["status"] == "draft"
        resp = accountant_client.post(f"{BASE}/invoices/{data['id']}/issue/")
        assert _data(resp)["status"] == "pending"

    def test_cancel(self, accountant_client, invoice_payload):
        inv = _data(accountant_client.post(f"{BASE}/invoices/", invoice_payload, format="json"))
        resp = accountant_client.post(f"{BASE}/invoices/{inv['id']}/cancel/")
        assert _data(resp)["status"] == "cancelled"

    def test_invoice_requires_lines(self, accountant_client, resident):
        resp = accountant_client.post(
            f"{BASE}/invoices/", {"resident": str(resident.id), "lines": []}, format="json"
        )
        assert resp.status_code == 400


class TestPaymentApi:
    def _invoice(self, client, payload):
        return _data(client.post(f"{BASE}/invoices/", payload, format="json"))

    def test_collect_settles_immediately(self, accountant_client, invoice_payload):
        inv = self._invoice(accountant_client, invoice_payload)
        resp = accountant_client.post(
            f"{BASE}/payments/",
            {"invoice": inv["id"], "amount": "7260.00", "method": "cash"},
            format="json",
        )
        assert resp.status_code == 201, resp.content
        data = _data(resp)
        assert data["status"] == "verified"
        assert data["receipt_number"].startswith("RCT-")
        invoice = Invoice.objects.get(id=inv["id"])
        assert invoice.status == Invoice.Status.PAID

    def test_require_verification_flow(self, accountant_client, invoice_payload):
        inv = self._invoice(accountant_client, invoice_payload)
        resp = accountant_client.post(
            f"{BASE}/payments/",
            {"invoice": inv["id"], "amount": "1000.00", "method": "bank_transfer",
             "require_verification": True},
            format="json",
        )
        data = _data(resp)
        assert data["status"] == "pending"
        assert data["receipt_number"] == ""
        assert Invoice.objects.get(id=inv["id"]).paid_amount == Decimal("0.00")

        resp = accountant_client.post(f"{BASE}/payments/{data['id']}/verify/")
        assert _data(resp)["status"] == "verified"
        assert Invoice.objects.get(id=inv["id"]).paid_amount == Decimal("1000.00")

    def test_payment_needs_invoice_or_resident(self, accountant_client):
        resp = accountant_client.post(
            f"{BASE}/payments/", {"amount": "100.00", "method": "cash"}, format="json"
        )
        assert resp.status_code == 400

    def test_verified_payment_cannot_be_deleted(self, accountant_client, invoice_payload):
        inv = self._invoice(accountant_client, invoice_payload)
        pay = _data(accountant_client.post(
            f"{BASE}/payments/", {"invoice": inv["id"], "amount": "500.00"}, format="json"
        ))
        resp = accountant_client.delete(f"{BASE}/payments/{pay['id']}/")
        assert resp.status_code == 400


class TestExpenseApi:
    def test_workflow_pending_approve_paid(self, accountant_client, hostel):
        resp = accountant_client.post(
            f"{BASE}/expenses/",
            {"title": "Generator fuel", "amount": "300.00", "payment_method": "cash"},
            format="json",
        )
        assert resp.status_code == 201
        data = _data(resp)
        assert data["status"] == "pending"

        accountant_client.post(f"{BASE}/expenses/{data['id']}/approve/")
        resp = accountant_client.post(f"{BASE}/expenses/{data['id']}/mark-paid/")
        assert _data(resp)["status"] == "paid"
        txn = LedgerTransaction.objects.get(entity_id=data["id"])
        assert txn.direction == "out"
        assert txn.amount == Decimal("300.00")

    def test_paid_expense_locked(self, accountant_client):
        exp = _data(accountant_client.post(
            f"{BASE}/expenses/", {"title": "Rent", "amount": "100.00"}, format="json"
        ))
        accountant_client.post(f"{BASE}/expenses/{exp['id']}/mark-paid/")
        resp = accountant_client.patch(
            f"{BASE}/expenses/{exp['id']}/", {"amount": "999.00"}, format="json"
        )
        assert resp.status_code == 400
        resp = accountant_client.delete(f"{BASE}/expenses/{exp['id']}/")
        assert resp.status_code == 400

    def test_rejected_expense_cannot_be_paid(self, accountant_client):
        exp = _data(accountant_client.post(
            f"{BASE}/expenses/", {"title": "Sofa", "amount": "50.00"}, format="json"
        ))
        accountant_client.post(f"{BASE}/expenses/{exp['id']}/reject/")
        resp = accountant_client.post(f"{BASE}/expenses/{exp['id']}/mark-paid/")
        assert resp.status_code == 400


class TestIncomeApi:
    def test_create_posts_ledger_and_delete_removes(self, accountant_client):
        resp = accountant_client.post(
            f"{BASE}/income/",
            {"title": "Cafeteria sales", "source": "cafeteria", "amount": "800.00"},
            format="json",
        )
        data = _data(resp)
        assert LedgerTransaction.objects.filter(entity_id=data["id"]).exists()
        accountant_client.delete(f"{BASE}/income/{data['id']}/")
        assert not LedgerTransaction.objects.filter(entity_id=data["id"]).exists()
        assert not Income.objects.filter(id=data["id"]).exists()


class TestRefundApi:
    def test_full_lifecycle(self, accountant_client, invoice_payload, resident):
        inv = _data(accountant_client.post(f"{BASE}/invoices/", invoice_payload, format="json"))
        pay = _data(accountant_client.post(
            f"{BASE}/payments/", {"invoice": inv["id"], "amount": "7260.00"}, format="json"
        ))
        resp = accountant_client.post(
            f"{BASE}/refunds/",
            {"refund_type": "withdrawal", "payment": pay["id"], "resident": str(resident.id),
             "amount": "7260.00", "reason": "Left hostel"},
            format="json",
        )
        refund = _data(resp)
        assert refund["status"] == "requested"

        # must be approved before processing
        resp = accountant_client.post(f"{BASE}/refunds/{refund['id']}/process/")
        assert resp.status_code == 400

        accountant_client.post(f"{BASE}/refunds/{refund['id']}/approve/")
        resp = accountant_client.post(f"{BASE}/refunds/{refund['id']}/process/")
        assert _data(resp)["status"] == "processed"
        assert PaymentRecord.objects.get(id=pay["id"]).status == PaymentRecord.Status.REFUNDED

    def test_refund_cannot_exceed_payment(self, accountant_client, invoice_payload):
        inv = _data(accountant_client.post(f"{BASE}/invoices/", invoice_payload, format="json"))
        pay = _data(accountant_client.post(
            f"{BASE}/payments/", {"invoice": inv["id"], "amount": "1000.00"}, format="json"
        ))
        resp = accountant_client.post(
            f"{BASE}/refunds/",
            {"payment": pay["id"], "amount": "2000.00", "reason": "Too much"},
            format="json",
        )
        assert resp.status_code == 400


class TestFeesApi:
    def test_categories_seeded_and_system_protected(self, accountant_client):
        cats = _data(accountant_client.get(f"{BASE}/fee-categories/"))
        assert any(c["name"] == "Hostel Fee" for c in cats)
        system = next(c for c in cats if c["is_system"])
        resp = accountant_client.delete(f"{BASE}/fee-categories/{system['id']}/")
        assert resp.status_code == 400

    def test_bulk_assignment(self, accountant_client, hostel, resident):
        from conftest import ResidentFactory

        other = ResidentFactory(hostel=hostel)
        fee = _data(accountant_client.post(
            f"{BASE}/fee-structures/",
            {"name": "Monthly rent", "amount": "5000.00", "recurrence": "monthly"},
            format="json",
        ))
        resp = accountant_client.post(
            f"{BASE}/fee-assignments/bulk-assign/",
            {"fee_structure": fee["id"], "resident_ids": [str(resident.id), str(other.id)]},
            format="json",
        )
        assert resp.status_code == 201
        assert _data(resp)["created"] == 2

    def test_waive_assignment(self, accountant_client, resident):
        fee = _data(accountant_client.post(
            f"{BASE}/fee-structures/", {"name": "Laundry", "amount": "500.00"}, format="json"
        ))
        assignment = _data(accountant_client.post(
            f"{BASE}/fee-assignments/",
            {"fee_structure": fee["id"], "resident": str(resident.id)},
            format="json",
        ))
        resp = accountant_client.post(
            f"{BASE}/fee-assignments/{assignment['id']}/waive/",
            {"reason": "Hardship"}, format="json",
        )
        data = _data(resp)
        assert data["status"] == "waived"
        assert data["waived_reason"] == "Hardship"


class TestScholarshipApi:
    def test_award_approval_flow(self, accountant_client, resident):
        sch = _data(accountant_client.post(
            f"{BASE}/scholarships/",
            {"name": "Merit 25", "award_type": "percentage", "value": "25"},
            format="json",
        ))
        award = _data(accountant_client.post(
            f"{BASE}/scholarship-awards/",
            {"scholarship": sch["id"], "resident": str(resident.id)},
            format="json",
        ))
        assert award["status"] == "pending"
        resp = accountant_client.post(f"{BASE}/scholarship-awards/{award['id']}/approve/")
        assert _data(resp)["status"] == "approved"


class TestDashboardAndReports:
    def test_summary_reflects_activity(self, accountant_client, invoice_payload):
        inv = _data(accountant_client.post(f"{BASE}/invoices/", invoice_payload, format="json"))
        accountant_client.post(
            f"{BASE}/payments/", {"invoice": inv["id"], "amount": "7260.00"}, format="json"
        )
        exp = _data(accountant_client.post(
            f"{BASE}/expenses/", {"title": "Fuel", "amount": "260.00"}, format="json"
        ))
        accountant_client.post(f"{BASE}/expenses/{exp['id']}/mark-paid/")

        resp = accountant_client.get(f"{BASE}/dashboard/summary/")
        assert resp.status_code == 200
        totals = _data(resp)["totals"]
        assert totals["total_revenue"] == "7260.00"
        assert totals["total_expenses"] == "260.00"
        assert totals["net_profit"] == "7000.00"
        assert totals["todays_collection"] == "7260.00"

    def test_profit_loss_report(self, accountant_client, invoice_payload):
        inv = _data(accountant_client.post(f"{BASE}/invoices/", invoice_payload, format="json"))
        accountant_client.post(
            f"{BASE}/payments/", {"invoice": inv["id"], "amount": "1000.00"}, format="json"
        )
        resp = accountant_client.get(f"{BASE}/reports/profit-loss/")
        data = _data(resp)
        assert data["total_income"] == "1000.00"
        assert data["net"] == "1000.00"

    def test_csv_export(self, accountant_client, invoice_payload):
        accountant_client.post(f"{BASE}/invoices/", invoice_payload, format="json")
        resp = accountant_client.get(f"{BASE}/reports/export/?type=invoices")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/csv"
        body = resp.content.decode()
        assert "INV-000001" in body

    def test_export_rejects_unknown_type(self, accountant_client):
        resp = accountant_client.get(f"{BASE}/reports/export/?type=secrets")
        assert resp.status_code == 400


class TestPermissions:
    def test_warden_can_view_but_not_create(self, warden_client, resident):
        assert warden_client.get(f"{BASE}/invoices/").status_code == 200
        resp = warden_client.post(
            f"{BASE}/invoices/",
            {"resident": str(resident.id),
             "lines": [{"description": "Fee", "unit_price": "100.00"}]},
            format="json",
        )
        assert resp.status_code == 403

    def test_warden_cannot_collect_or_export(self, warden_client):
        assert warden_client.post(
            f"{BASE}/payments/", {"amount": "10.00"}, format="json"
        ).status_code == 403
        assert warden_client.get(f"{BASE}/reports/export/?type=invoices").status_code == 403

    def test_resident_role_denied(self, auth_client, resident_user, hostel):
        client = auth_client(resident_user, hostel)
        assert client.get(f"{BASE}/invoices/").status_code == 403
        assert client.get(f"{BASE}/dashboard/summary/").status_code == 403

    def test_anonymous_denied(self, api):
        assert api.get(f"{BASE}/invoices/").status_code in (401, 403)

    def test_expense_approval_needs_approve_permission(self, warden_client, accountant_client):
        exp = _data(accountant_client.post(
            f"{BASE}/expenses/", {"title": "Paint", "amount": "80.00"}, format="json"
        ))
        assert warden_client.post(f"{BASE}/expenses/{exp['id']}/approve/").status_code == 403
