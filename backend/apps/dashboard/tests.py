"""Tests for the system-status dashboard (heartbeat + aggregates)."""
import pytest

from apps.dashboard.models import UserPresence
from apps.notifications.models import PushSubscription

pytestmark = pytest.mark.django_db

HEARTBEAT = "/api/dashboard/heartbeat/"
STATUS = "/api/dashboard/system-status/"


def test_heartbeat_records_presence(auth_client, warden, hostel):
    client = auth_client(warden, hostel)
    resp = client.post(
        HEARTBEAT, {"installed": True, "sw_version": "v3.0.0", "app_version": "1.0.0"}, format="json"
    )
    assert resp.status_code == 200
    p = UserPresence.objects.get(user=warden, hostel=hostel)
    assert p.is_installed is True
    assert p.sw_version == "v3.0.0"


def test_heartbeat_is_idempotent_per_user(auth_client, warden, hostel):
    client = auth_client(warden, hostel)
    client.post(HEARTBEAT, {"installed": False}, format="json")
    client.post(HEARTBEAT, {"installed": True}, format="json")
    assert UserPresence.objects.filter(user=warden, hostel=hostel).count() == 1


def test_system_status_counts(auth_client, make_user, hostel):
    owner = make_user(role="OWNER", hostel=hostel)
    resident = make_user(role="RESIDENT", hostel=hostel)
    # owner + resident online; resident installed
    auth_client(owner, hostel).post(HEARTBEAT, {"installed": False}, format="json")
    auth_client(resident, hostel).post(HEARTBEAT, {"installed": True}, format="json")
    PushSubscription.objects.create(
        user=resident, hostel=hostel, endpoint="https://push/x", p256dh="k", auth="a"
    )

    resp = auth_client(owner, hostel).get(STATUS)
    assert resp.status_code == 200
    data = resp.data
    assert data["users"]["members"] == 2
    assert data["users"]["online"] == 2
    assert data["users"]["installed_active"] == 1
    assert data["pwa"]["push_subscribers"] == 1
    assert "api_health" in data
    assert set(data["sync"]) == {"pending", "failed"}


def test_system_status_requires_staff(auth_client, resident_user, hostel):
    resp = auth_client(resident_user, hostel).get(STATUS)
    assert resp.status_code == 403


def test_offline_derived_from_window(auth_client, make_user, hostel):
    owner = make_user(role="OWNER", hostel=hostel)
    make_user(role="RESIDENT", hostel=hostel)  # never sends a heartbeat → offline
    auth_client(owner, hostel).post(HEARTBEAT, {}, format="json")

    data = auth_client(owner, hostel).get(STATUS).data
    assert data["users"]["members"] == 2
    assert data["users"]["online"] == 1
    assert data["users"]["offline"] == 1
