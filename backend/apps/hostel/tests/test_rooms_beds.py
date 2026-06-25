"""Rooms & beds: uniqueness constraints + tenant scoping (Phase 10 §3 capacity).

Track A inventory model: hostel.Room / hostel.Bed.
"""
import pytest
from django.db import IntegrityError, transaction

from apps.hostel.models import Bed, Room

ROOMS = "/api/hostel/rooms/"
BEDS = "/api/hostel/beds/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client(auth_client, make_user, hostel):
    return auth_client(make_user(role="WARDEN", hostel=hostel), hostel)


# --- DB-level integrity -----------------------------------------------------
def test_room_number_unique_per_hostel(hostel):
    Room.objects.create(hostel=hostel, number="101")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Room.objects.create(hostel=hostel, number="101")


def test_same_room_number_allowed_in_different_hostels(hostel, other_hostel):
    Room.objects.create(hostel=hostel, number="101")
    Room.objects.create(hostel=other_hostel, number="101")  # no clash across tenants
    assert Room.objects.filter(number="101").count() == 2


def test_bed_label_unique_per_room(hostel, room):
    Bed.objects.create(hostel=hostel, room=room, label="A")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Bed.objects.create(hostel=hostel, room=room, label="A")


# --- API behaviour ----------------------------------------------------------
def test_create_room_scopes_to_caller_hostel(staff_client, hostel):
    resp = staff_client.post(ROOMS, {"number": "201", "floor": "2"})
    assert resp.status_code == 201
    assert Room.objects.get(number="201").hostel_id == hostel.id


def test_room_list_scoped(staff_client, hostel, other_hostel):
    Room.objects.create(hostel=hostel, number="A")
    Room.objects.create(hostel=other_hostel, number="B")
    resp = staff_client.get(ROOMS)
    assert resp.status_code == 200
    assert resp.data["count"] == 1


def test_create_bed_in_room(staff_client, hostel, room):
    resp = staff_client.post(BEDS, {"room": room.id, "label": "C"})
    assert resp.status_code == 201
    assert Bed.objects.get(label="C", room=room).hostel_id == hostel.id


def test_resident_role_cannot_create_room(auth_client, resident_user, hostel):
    assert auth_client(resident_user, hostel).post(ROOMS, {"number": "X"}).status_code == 403
