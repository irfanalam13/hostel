"""Negative tests for residents (Phase 10 §8).

Invalid payloads, wrong types, unauthorized access, injection payloads.
"""
import pytest

from apps.residents.models import Resident

RESIDENTS = "/api/residents/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client(auth_client, make_user, hostel):
    return auth_client(make_user(role="WARDEN", hostel=hostel), hostel)


def test_missing_required_full_name_rejected(staff_client):
    resp = staff_client.post(RESIDENTS, {"phone": "9810000000"})
    assert resp.status_code == 400
    assert "full_name" in resp.data


def test_wrong_type_for_bed_rejected(staff_client):
    resp = staff_client.post(RESIDENTS, {"full_name": "X", "current_bed": "not-an-id"})
    assert resp.status_code == 400


def test_bad_status_choice_rejected(staff_client):
    resp = staff_client.post(RESIDENTS, {"full_name": "X", "status": "teleported"})
    assert resp.status_code == 400


def test_unauthenticated_cannot_create(api, hostel):
    api.credentials(HTTP_X_HOSTEL_CODE=hostel.code)
    assert api.post(RESIDENTS, {"full_name": "X"}).status_code in (401, 403)


def test_sql_injection_payload_is_treated_as_data(staff_client):
    """An injection string must be stored verbatim, never executed."""
    payload = "Robert'); DROP TABLE residents_resident;--"
    resp = staff_client.post(RESIDENTS, {"full_name": payload})
    assert resp.status_code == 201
    # The table still exists and the value is stored literally.
    assert Resident.objects.filter(full_name=payload).exists()


def test_xss_payload_stored_not_interpreted(staff_client):
    payload = "<script>alert('x')</script>"
    resp = staff_client.post(RESIDENTS, {"full_name": payload})
    assert resp.status_code == 201
    r = Resident.objects.get(full_name=payload)
    # Stored verbatim; escaping is the client/renderer's concern, not mutation.
    assert r.full_name == payload


def test_cannot_act_on_other_hostel_resident(auth_client, make_user, hostel, other_hostel):
    """Checkout/detail on a resident from another tenant must 404 (scoped qs)."""
    from conftest import ResidentFactory

    foreign = ResidentFactory(hostel=other_hostel)
    user = make_user(role="WARDEN", hostel=hostel)
    resp = auth_client(user, hostel).post(f"{RESIDENTS}{foreign.id}/checkout/")
    assert resp.status_code == 404
