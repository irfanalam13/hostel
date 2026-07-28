"""Self-service profile edit (MeView.patch).

Covered:
  * updates name + email and persists them
  * rejects an email already used by another user
  * allows re-saving your own unchanged email
  * ignores attempts to smuggle role/username changes through the whitelist
  * requires authentication
  * records an audit event
"""
import pytest

from apps.auditlog.models import AuditEvent

ME = "/api/auth/me/"

pytestmark = pytest.mark.django_db


def test_patch_updates_name_and_email(auth_client, warden, hostel):
    resp = auth_client(warden, hostel).patch(
        ME, {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"}
    )
    assert resp.status_code == 200
    assert resp.data["first_name"] == "Jane"
    assert resp.data["last_name"] == "Doe"
    assert resp.data["email"] == "jane@example.com"

    warden.refresh_from_db()
    assert warden.first_name == "Jane"
    assert warden.email == "jane@example.com"


def test_patch_rejects_email_already_in_use_by_another_user(auth_client, warden, make_user, hostel):
    make_user(role="WARDEN", hostel=hostel, email="taken@example.com")

    resp = auth_client(warden, hostel).patch(ME, {"email": "taken@example.com"})
    assert resp.status_code == 400


def test_patch_allows_reusing_own_current_email(auth_client, warden, hostel):
    resp = auth_client(warden, hostel).patch(ME, {"email": warden.email})
    assert resp.status_code == 200


def test_patch_does_not_allow_role_or_username_change(auth_client, warden, hostel):
    original_username = warden.username
    resp = auth_client(warden, hostel).patch(
        ME, {"role": "OWNER", "username": "hijack", "first_name": "Ok"}
    )
    assert resp.status_code == 200

    warden.refresh_from_db()
    assert warden.role == "WARDEN"
    assert warden.username == original_username
    assert warden.first_name == "Ok"


def test_patch_requires_auth(api):
    assert api.patch(ME, {"first_name": "Nope"}).status_code == 401


def test_patch_records_audit_event(auth_client, warden, hostel):
    auth_client(warden, hostel).patch(ME, {"first_name": "Jane"})
    assert AuditEvent.objects.filter(
        actor=warden,
        action=AuditEvent.Action.UPDATE,
        message="Profile updated",
    ).exists()
