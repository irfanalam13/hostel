"""PlatformAuditEventViewSet — cross-tenant audit trail for super-admins,
reachable without any hostel context (unlike the tenant-facing endpoint)."""
import pytest

from apps.auditlog.models import AuditEvent

URL = "/api/platform/audit/events/"

pytestmark = pytest.mark.django_db


def _event(hostel, message):
    return AuditEvent.objects.create(
        hostel_id=hostel.id, action=AuditEvent.Action.LOGIN, message=message
    )


def _messages(payload):
    rows = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
    results = rows["results"] if isinstance(rows, dict) and "results" in rows else rows
    return {r["message"] for r in results}


def test_superuser_sees_all_workspaces(superuser, hostel, other_hostel, auth_client):
    _event(hostel, "one")
    _event(other_hostel, "two")

    resp = auth_client(superuser, hostel).get(URL)
    assert resp.status_code == 200
    assert {"one", "two"} <= _messages(resp.json())


def test_tenant_owner_denied(owner, hostel, auth_client):
    resp = auth_client(owner, hostel).get(URL)
    assert resp.status_code == 403


def test_anonymous_denied(api):
    assert api.get(URL).status_code in (401, 403)
