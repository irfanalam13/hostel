"""Super-Admin hostel drill-down (Overview/Students/Staff/Rooms tabs).

Strictly read-only cross-tenant views — a tenant OWNER must never reach
another workspace's data, and every endpoint here must refuse writes
(405) regardless of caller, since the Super Admin section is read-only by
design for hostel-operational data.
"""
import datetime as dt
from decimal import Decimal

import pytest

from apps.common.utils import month_key
from apps.fees.models import FeeLedger
from apps.payments.models import Payment
from apps.rooms.models import Bed, BedAssignment, Room
from apps.staff.models import StaffProfile
from apps.students.models import Student

pytestmark = pytest.mark.django_db

DETAIL = "/api/platform/hostels/{id}/"
STUDENTS = "/api/platform/hostels/{id}/students/"
DUES = "/api/platform/hostels/{id}/students/{student_id}/dues/"
STAFF = "/api/platform/hostels/{id}/staff/"
ROOMS = "/api/platform/hostels/{id}/rooms/"

ALL_URLS = [DETAIL, STUDENTS, STAFF, ROOMS]


def _make_student(hostel, **kwargs):
    return Student.objects.create(
        hostel=hostel,
        full_name=kwargs.pop("full_name", "Test Student"),
        phone=kwargs.pop("phone", "9800000000"),
        join_date=kwargs.pop("join_date", dt.date(2026, 1, 1)),
        **kwargs,
    )


def _make_room_and_bed(hostel, *, bed_status="AVAILABLE"):
    room = Room.objects.create(hostel=hostel, room_no=f"R-{Room.objects.filter(hostel=hostel).count()}")
    bed = Bed.objects.create(hostel=hostel, room=room, bed_no="1", status=bed_status)
    return room, bed


def _payload(resp):
    data = resp.json()
    return data["data"] if isinstance(data, dict) and "data" in data else data


def test_hostel_detail_overview(superuser, hostel, auth_client):
    student = _make_student(hostel)
    _, bed = _make_room_and_bed(hostel, bed_status="OCCUPIED")
    Payment.objects.create(hostel=hostel, student=student, amount=Decimal("15000.00"), date=dt.date.today())
    FeeLedger.objects.create(
        hostel=hostel, student=student, month=month_key(dt.date.today()),
        amount=Decimal("5000.00"), net_due=Decimal("5000.00"), status="DUE",
    )

    resp = auth_client(superuser, hostel).get(DETAIL.format(id=hostel.id))
    assert resp.status_code == 200
    row = _payload(resp)
    assert row["id"] == str(hostel.id)
    assert row["name"] == hostel.name
    assert Decimal(row["revenue_summary"]["month_revenue"]) == Decimal("15000.00")
    assert Decimal(row["revenue_summary"]["month_due"]) == Decimal("5000.00")
    assert row["usage"]["active_students"] == 1
    assert row["usage"]["beds_total"] == 1
    assert row["usage"]["beds_occupied"] == 1


def test_hostel_detail_404_for_unknown_id(superuser, hostel, auth_client):
    resp = auth_client(superuser, hostel).get(DETAIL.format(id="00000000-0000-0000-0000-000000000000"))
    assert resp.status_code == 404


def test_students_roster_scoped_to_hostel(superuser, hostel, other_hostel, auth_client):
    mine = _make_student(hostel, full_name="Mine")
    _make_student(other_hostel, full_name="Theirs")
    room, bed = _make_room_and_bed(hostel, bed_status="OCCUPIED")
    BedAssignment.objects.create(hostel=hostel, bed=bed, student=mine, start_date=dt.date.today())
    FeeLedger.objects.create(
        hostel=hostel, student=mine, month=month_key(dt.date.today()),
        amount=Decimal("5000.00"), net_due=Decimal("5000.00"), status="DUE",
    )

    resp = auth_client(superuser, hostel).get(STUDENTS.format(id=hostel.id))
    assert resp.status_code == 200
    rows = _payload(resp)
    assert len(rows) == 1
    assert rows[0]["full_name"] == "Mine"
    assert rows[0]["room_no"] == room.room_no
    assert rows[0]["bed_no"] == bed.bed_no
    assert rows[0]["current_month_status"] == "DUE"
    assert Decimal(rows[0]["total_outstanding"]) == Decimal("5000.00")


def test_student_dues_history(superuser, hostel, auth_client):
    student = _make_student(hostel)
    FeeLedger.objects.create(
        hostel=hostel, student=student, month="2026-01",
        amount=Decimal("5000.00"), net_due=Decimal("5000.00"), status="PAID",
    )
    FeeLedger.objects.create(
        hostel=hostel, student=student, month="2026-02",
        amount=Decimal("5000.00"), net_due=Decimal("2000.00"), status="PARTIAL",
    )

    resp = auth_client(superuser, hostel).get(DUES.format(id=hostel.id, student_id=student.id))
    assert resp.status_code == 200
    rows = _payload(resp)
    assert [r["month"] for r in rows] == ["2026-02", "2026-01"]


def test_student_dues_404_for_cross_hostel_student(superuser, hostel, other_hostel, auth_client):
    foreign_student = _make_student(other_hostel)
    resp = auth_client(superuser, hostel).get(DUES.format(id=hostel.id, student_id=foreign_student.id))
    assert resp.status_code == 404


def test_staff_directory_scoped_to_hostel(superuser, hostel, other_hostel, auth_client, make_user):
    mine_user = make_user(role="WARDEN", hostel=hostel, username="mystaff")
    theirs_user = make_user(role="WARDEN", hostel=other_hostel, username="theirstaff")
    StaffProfile.objects.create(hostel=hostel, user=mine_user, employee_id="E1", first_name="Mine")
    StaffProfile.objects.create(hostel=other_hostel, user=theirs_user, employee_id="E1", first_name="Theirs")

    resp = auth_client(superuser, hostel).get(STAFF.format(id=hostel.id))
    assert resp.status_code == 200
    rows = _payload(resp)
    names = [r["full_name"] for r in rows]
    assert "Mine" in names
    assert "Theirs" not in names


def test_rooms_occupancy_scoped_to_hostel(superuser, hostel, other_hostel, auth_client):
    room, bed = _make_room_and_bed(hostel, bed_status="OCCUPIED")
    Bed.objects.create(hostel=hostel, room=room, bed_no="2", status="AVAILABLE")
    _make_room_and_bed(other_hostel, bed_status="OCCUPIED")

    resp = auth_client(superuser, hostel).get(ROOMS.format(id=hostel.id))
    assert resp.status_code == 200
    rows = _payload(resp)
    assert len(rows) == 1
    assert rows[0]["room_no"] == room.room_no
    assert rows[0]["beds_total"] == 2
    assert rows[0]["beds_occupied"] == 1


@pytest.mark.parametrize("url_tpl", ALL_URLS)
def test_tenant_owner_denied(url_tpl, owner, hostel, auth_client):
    resp = auth_client(owner, hostel).get(url_tpl.format(id=hostel.id))
    assert resp.status_code == 403


@pytest.mark.parametrize("url_tpl", ALL_URLS)
def test_anonymous_denied(url_tpl, hostel, api):
    resp = api.get(url_tpl.format(id=hostel.id))
    assert resp.status_code in (401, 403)


@pytest.mark.parametrize("url_tpl", ALL_URLS)
@pytest.mark.parametrize("method", ["post", "patch", "put", "delete"])
def test_read_only_rejects_writes(url_tpl, method, superuser, hostel, auth_client):
    client = auth_client(superuser, hostel)
    resp = getattr(client, method)(url_tpl.format(id=hostel.id), {})
    assert resp.status_code == 405


def test_student_dues_read_only_rejects_writes(superuser, hostel, auth_client):
    student = _make_student(hostel)
    client = auth_client(superuser, hostel)
    for method in ("post", "patch", "put", "delete"):
        resp = getattr(client, method)(DUES.format(id=hostel.id, student_id=student.id), {})
        assert resp.status_code == 405
