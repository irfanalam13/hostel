"""Audit-log tenant isolation.

Regression guard for the cross-tenant leak fixed in the Authentication Flow
Refactor: `AuditEventViewSet` used to expose `AuditEvent.objects.all()` with
only a role check, so an owner/manager of one workspace could read every
tenant's audit events. Events must now be scoped to the caller's workspace.
"""
import pytest

from apps.auditlog.models import AuditEvent

AUDIT_URL = "/api/audit/events/"


def _event(hostel, message):
    return AuditEvent.objects.create(
        hostel_id=hostel.id,
        action=AuditEvent.Action.LOGIN,
        message=message,
    )


@pytest.mark.django_db
def test_owner_sees_only_their_workspace_events(owner, hostel, other_hostel, auth_client):
    _event(hostel, "mine")
    _event(other_hostel, "theirs")

    resp = auth_client(owner, hostel).get(AUDIT_URL)
    assert resp.status_code == 200

    payload = resp.json()
    rows = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
    results = rows["results"] if isinstance(rows, dict) and "results" in rows else rows
    messages = {r["message"] for r in results}

    assert "mine" in messages
    assert "theirs" not in messages  # cross-tenant event must never leak


@pytest.mark.django_db
def test_non_member_owner_cannot_read_another_workspace(make_user, hostel, other_hostel, auth_client):
    """An owner of `other_hostel` gets none of `hostel`'s events even if they
    aim their session at it — membership + scoping both apply."""
    _event(hostel, "secret")
    outsider = make_user(role="OWNER", hostel=other_hostel)

    resp = auth_client(outsider, other_hostel).get(AUDIT_URL)
    assert resp.status_code == 200
    payload = resp.json()
    rows = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
    results = rows["results"] if isinstance(rows, dict) and "results" in rows else rows
    assert all(r["message"] != "secret" for r in results)


@pytest.mark.django_db
def test_superuser_sees_all_workspaces(superuser, hostel, other_hostel, auth_client):
    _event(hostel, "one")
    _event(other_hostel, "two")

    resp = auth_client(superuser, hostel).get(AUDIT_URL)
    assert resp.status_code == 200
    payload = resp.json()
    rows = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
    results = rows["results"] if isinstance(rows, dict) and "results" in rows else rows
    messages = {r["message"] for r in results}
    assert {"one", "two"} <= messages
