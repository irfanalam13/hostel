"""Disaster-recovery API authorization (Phase 9 — platform-surface gating).

The *global* DR surfaces — the mode switch and the status overview — must be
super-admin only. A tenant ``ADMIN`` (a hostel-level role) must not be able to
flip the platform-wide DR mode or read every tenant's restore history.

Per-hostel operations (restore, backup validate) keep the looser ``IsDRAdmin``
gate because they are additionally guarded by a membership check
(``_can_touch_hostel``); those are covered elsewhere.
"""
import pytest

DR_MODE_URL = "/api/admin/dr/mode/"
DR_STATUS_URL = "/api/admin/dr/status/"


@pytest.mark.django_db
def test_tenant_admin_cannot_switch_global_dr_mode(make_user, hostel, auth_client):
    admin = make_user(role="ADMIN", hostel=hostel)
    resp = auth_client(admin, hostel).post(
        DR_MODE_URL, {"mode": "maintenance"}, format="json"
    )
    assert resp.status_code == 403  # global surface — super admin only


@pytest.mark.django_db
def test_tenant_admin_cannot_read_global_dr_status(make_user, hostel, auth_client):
    admin = make_user(role="ADMIN", hostel=hostel)
    resp = auth_client(admin, hostel).get(DR_STATUS_URL)
    assert resp.status_code == 403  # no cross-tenant restore-history leak


@pytest.mark.django_db
def test_superuser_can_switch_and_read_dr(superuser, hostel, auth_client):
    client = auth_client(superuser, hostel)
    assert client.get(DR_STATUS_URL).status_code == 200
    resp = client.post(DR_MODE_URL, {"mode": "normal"}, format="json")
    assert resp.status_code == 200
    # Responses are wrapped in a {"data": ...} envelope by the common renderer.
    payload = resp.json()
    data = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
    assert data["mode"] == "normal"
