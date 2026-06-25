"""Hostel/tenant model + API (Phase 10 §2 tenant isolation foundation)."""
import pytest

from apps.tenants.models import Hostel

HOSTELS = "/api/tenants/hostels/"
PLANS = "/api/tenants/plans/"

pytestmark = pytest.mark.django_db


def test_code_autogenerates_and_is_unique(db):
    h1 = Hostel.objects.create(name="A")
    h2 = Hostel.objects.create(name="B")
    assert h1.code and h2.code
    assert h1.code != h2.code
    assert h1.code.startswith("H-")


def test_explicit_code_preserved(db):
    h = Hostel.objects.create(name="A", code="H-CUSTOM")
    assert h.code == "H-CUSTOM"


def test_hostels_list_scoped_to_membership(auth_client, make_user, hostel, other_hostel):
    user = make_user(role="OWNER", hostel=hostel)  # member of `hostel` only
    resp = auth_client(user, hostel).get(HOSTELS)
    assert resp.status_code == 200
    codes = [h["code"] for h in resp.data["results"]]
    assert hostel.code in codes
    assert other_hostel.code not in codes


def test_non_owner_cannot_create_hostel(auth_client, make_user, hostel):
    warden = make_user(role="WARDEN", hostel=hostel)
    resp = auth_client(warden, hostel).post(HOSTELS, {"name": "New One"})
    assert resp.status_code == 403


def test_plans_require_auth(api, auth_client, owner, hostel):
    assert api.get(PLANS).status_code in (401, 403)
    assert auth_client(owner, hostel).get(PLANS).status_code == 200
