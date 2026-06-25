"""End-to-end API flows that cross app boundaries (Phase 10 §7).

These drive the real HTTP stack (auth + tenant resolution + permissions +
serializers + services), not isolated units.
"""
from decimal import Decimal

import pytest

from apps.billing.models import MonthlyDue, Payment
from apps.residents.models import Resident

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def test_admit_room_bed_bill_pay_checkout(auth_client, make_user, hostel):
    """Owner sets up inventory; warden admits a resident, bills, collects, checks out."""
    owner = make_user(role="OWNER", hostel=hostel)
    warden = make_user(role="WARDEN", hostel=hostel)
    owner_c = auth_client(owner, hostel)
    warden_c = auth_client(warden, hostel)

    # 1. Owner creates a room + bed.
    room_id = owner_c.post("/api/hostel/rooms/", {"number": "101", "floor": "1"}).data["id"]
    bed_id = owner_c.post("/api/hostel/beds/", {"room": room_id, "label": "A"}).data["id"]

    # 2. Warden admits a resident onto that bed.
    r = warden_c.post(
        "/api/residents/",
        {"full_name": "Integration Resident", "current_bed": bed_id, "monthly_fee": "5000.00"},
    )
    assert r.status_code == 201
    rid = r.data["id"]

    # 3. Warden generates this month's due.
    due_id = warden_c.post(
        "/api/billing/dues/",
        {"resident": rid, "year": 2026, "month": 6, "amount": "5000.00"},
    ).data["id"]

    # 4. Resident pays in full.
    pay = warden_c.post(
        "/api/billing/payments/",
        {"resident": rid, "due": due_id, "amount": "5000.00"},
    )
    assert pay.status_code == 201
    assert MonthlyDue.objects.get(id=due_id).remaining == 0

    # 5. Checkout now succeeds (nothing outstanding).
    out = warden_c.post(f"/api/residents/{rid}/checkout/")
    assert out.status_code == 200

    resident = Resident.objects.get(id=rid)
    assert resident.status == "left"
    assert resident.current_bed is None
    assert Payment.objects.filter(resident=resident).count() == 1


def test_checkout_blocked_until_paid_then_succeeds(auth_client, make_user, hostel):
    warden = make_user(role="WARDEN", hostel=hostel)
    c = auth_client(warden, hostel)

    rid = c.post("/api/residents/", {"full_name": "Debtor"}).data["id"]
    due_id = c.post(
        "/api/billing/dues/", {"resident": rid, "year": 2026, "month": 6, "amount": "5000.00"}
    ).data["id"]

    # Outstanding -> blocked.
    assert c.post(f"/api/residents/{rid}/checkout/").status_code == 400

    # Pay, then checkout clears.
    c.post("/api/billing/payments/", {"resident": rid, "due": due_id, "amount": "5000.00"})
    assert c.post(f"/api/residents/{rid}/checkout/").status_code == 200
