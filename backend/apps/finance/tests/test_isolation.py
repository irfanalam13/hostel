"""Cross-tenant isolation for the finance module: rows from another workspace
are invisible and unreferenceable, even with a valid session."""
from decimal import Decimal

import pytest

from conftest import ResidentFactory

from apps.finance import services
from apps.finance.models import Discount, FeeStructure

pytestmark = pytest.mark.django_db

BASE = "/api/finance"


def _data(resp):
    return resp.json()["data"]


@pytest.fixture
def accountant_client(auth_client, accountant, hostel):
    return auth_client(accountant, hostel)


@pytest.fixture
def other_invoice(other_hostel, make_user):
    actor = make_user(role="OWNER", hostel=other_hostel)
    resident = ResidentFactory(hostel=other_hostel)
    return services.create_invoice(
        hostel=other_hostel, actor=actor, resident=resident,
        lines=[{"description": "Fee", "unit_price": "9000.00"}],
    )


def test_other_tenant_invoices_invisible(accountant_client, other_invoice):
    rows = _data(accountant_client.get(f"{BASE}/invoices/"))
    assert rows == []
    resp = accountant_client.get(f"{BASE}/invoices/{other_invoice.id}/")
    assert resp.status_code == 404


def test_cannot_pay_other_tenants_invoice(accountant_client, other_invoice):
    resp = accountant_client.post(
        f"{BASE}/payments/",
        {"invoice": str(other_invoice.id), "amount": "100.00"},
        format="json",
    )
    assert resp.status_code == 400


def test_cannot_assign_fee_to_other_tenants_resident(accountant_client, hostel, other_hostel):
    fee = FeeStructure.objects.create(hostel=hostel, name="Rent", amount=Decimal("1000.00"))
    outsider = ResidentFactory(hostel=other_hostel)
    resp = accountant_client.post(
        f"{BASE}/fee-assignments/",
        {"fee_structure": str(fee.id), "resident": str(outsider.id)},
        format="json",
    )
    assert resp.status_code == 400


def test_invoice_cannot_reference_other_tenants_discount(
    accountant_client, resident, other_hostel
):
    foreign = Discount.objects.create(
        hostel=other_hostel, name="Foreign", discount_type="fixed", value=Decimal("50.00"),
    )
    resp = accountant_client.post(
        f"{BASE}/invoices/",
        {
            "resident": str(resident.id),
            "lines": [{"description": "Fee", "unit_price": "100.00"}],
            "adjustments": [{"kind": "discount", "discount": str(foreign.id)}],
        },
        format="json",
    )
    assert resp.status_code == 400


def test_ledger_and_dashboard_are_tenant_scoped(
    accountant_client, other_invoice, other_hostel, make_user, auth_client
):
    # Settle a payment in the OTHER workspace, then confirm ours sees nothing.
    from apps.finance.models import PaymentRecord

    payment = PaymentRecord.objects.create(
        hostel=other_hostel, invoice=other_invoice,
        amount=Decimal("9000.00"), status=PaymentRecord.Status.PENDING,
    )
    services.settle_payment(payment)

    assert _data(accountant_client.get(f"{BASE}/transactions/")) == []
    totals = _data(accountant_client.get(f"{BASE}/dashboard/summary/"))["totals"]
    assert totals["total_revenue"] == "0.00"
