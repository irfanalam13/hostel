"""Multi-tenant isolation — the core SaaS safety property.

Covered (Phase 10 §2 critical checks):
  * cross-hostel access prevention (spoofed X-Hostel-Code)
  * membership enforcement (IsHostelResolved / HasHostelContext)
  * querysets never leak another tenant's rows
  * missing hostel context is rejected
"""
import pytest

from conftest import ResidentFactory

RESIDENTS = "/api/residents/"

pytestmark = pytest.mark.django_db


def test_member_only_sees_own_hostel_residents(auth_client, make_user, hostel, other_hostel):
    ResidentFactory(hostel=hostel, full_name="Mine")
    ResidentFactory(hostel=other_hostel, full_name="Theirs")
    user = make_user(role="WARDEN", hostel=hostel)

    resp = auth_client(user, hostel).get(RESIDENTS)
    assert resp.status_code == 200
    names = [r["full_name"] for r in resp.data["results"]]
    assert names == ["Mine"]


def test_spoofed_hostel_code_is_rejected(auth_client, make_user, hostel, other_hostel):
    """A user of hostel A with a token scoped to hostel B is denied."""
    ResidentFactory(hostel=other_hostel, full_name="Theirs")
    user = make_user(role="WARDEN", hostel=hostel)  # member of A only

    # auth_client scopes to other_hostel (B) — user is not a member of B.
    resp = auth_client(user, other_hostel).get(RESIDENTS)
    assert resp.status_code == 401


def test_missing_hostel_context_is_rejected(auth_client, make_user, hostel):
    user = make_user(role="WARDEN", hostel=hostel)
    resp = auth_client(user, hostel=None).get(RESIDENTS)
    assert resp.status_code == 401


def test_inactive_membership_is_denied(auth_client, make_user, hostel):
    from apps.accounts.models import UserHostel

    user = make_user(role="WARDEN", hostel=hostel)
    UserHostel.objects.filter(user=user, hostel=hostel).update(is_active=False)
    resp = auth_client(user, hostel).get(RESIDENTS)
    assert resp.status_code == 401


def test_anonymous_with_valid_code_cannot_read(api, hostel):
    api.credentials(HTTP_X_HOSTEL_CODE=hostel.code)
    resp = api.get(RESIDENTS)
    assert resp.status_code in (401, 403)


def test_writes_are_scoped_to_the_callers_hostel(auth_client, make_user, hostel):
    """A created resident is forced onto the caller's hostel, never a spoofed one."""
    user = make_user(role="WARDEN", hostel=hostel)
    resp = auth_client(user, hostel).post(RESIDENTS, {"full_name": "Scoped Person"})
    assert resp.status_code == 201

    from apps.residents.models import Resident

    created = Resident.objects.get(full_name="Scoped Person")
    assert created.hostel_id == hostel.id
