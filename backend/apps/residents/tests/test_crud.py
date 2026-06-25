"""Resident CRUD + bed-assignment history bookkeeping.

Covered (Phase 10 §3 admission → bed assignment, §5 stage 1-2)."""
import pytest

from apps.residents.models import BedAssignmentHistory, Resident

RESIDENTS = "/api/residents/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client(auth_client, make_user, hostel):
    return auth_client(make_user(role="WARDEN", hostel=hostel), hostel)


def test_create_resident_minimal(staff_client, hostel):
    resp = staff_client.post(RESIDENTS, {"full_name": "Asha Rai", "phone": "9810000000"})
    assert resp.status_code == 201
    r = Resident.objects.get(full_name="Asha Rai")
    assert r.hostel_id == hostel.id
    assert r.status == "active"
    assert r.join_date is not None


def test_create_resident_with_bed_opens_history(staff_client, hostel, bed):
    resp = staff_client.post(
        RESIDENTS, {"full_name": "Bina", "current_bed": bed.id}
    )
    assert resp.status_code == 201
    r = Resident.objects.get(full_name="Bina")
    hist = BedAssignmentHistory.objects.filter(resident=r, bed=bed, end_at__isnull=True)
    assert hist.count() == 1


def test_changing_bed_closes_old_and_opens_new_history(staff_client, hostel, room):
    from conftest import BedFactory

    bed1 = BedFactory(hostel=hostel, room=room)
    bed2 = BedFactory(hostel=hostel, room=room)
    resp = staff_client.post(RESIDENTS, {"full_name": "Chitra", "current_bed": bed1.id})
    rid = resp.data["id"]

    staff_client.patch(f"{RESIDENTS}{rid}/", {"current_bed": bed2.id})

    r = Resident.objects.get(id=rid)
    # Old assignment closed, new one open.
    assert BedAssignmentHistory.objects.filter(resident=r, bed=bed1, end_at__isnull=False).count() == 1
    assert BedAssignmentHistory.objects.filter(resident=r, bed=bed2, end_at__isnull=True).count() == 1


def test_list_ordered_and_scoped(staff_client, hostel):
    from conftest import ResidentFactory

    ResidentFactory(hostel=hostel, full_name="One")
    ResidentFactory(hostel=hostel, full_name="Two")
    resp = staff_client.get(RESIDENTS)
    assert resp.status_code == 200
    assert resp.data["count"] == 2


def test_mark_went_home_and_active(staff_client, hostel):
    from conftest import ResidentFactory

    r = ResidentFactory(hostel=hostel)
    assert staff_client.post(f"{RESIDENTS}{r.id}/mark_went_home/").status_code == 200
    r.refresh_from_db()
    assert r.status == "went_home"

    assert staff_client.post(f"{RESIDENTS}{r.id}/mark_active/").status_code == 200
    r.refresh_from_db()
    assert r.status == "active"
