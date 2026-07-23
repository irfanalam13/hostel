"""Workspace API: availability checker, registration, lifecycle endpoints,
permissions and cross-tenant isolation."""
import pytest

from apps.tenants import services
from apps.tenants.models import Hostel, WorkspaceStatus

pytestmark = pytest.mark.django_db

AVAIL = "/api/tenants/workspaces/availability/"
WORKSPACES = "/api/tenants/workspaces/"


def _data(resp):
    """Unwrap the StandardJSONRenderer envelope if present."""
    body = resp.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


# --- Availability checker (public) -------------------------------------------
def test_available_username(api, db):
    resp = api.get(AVAIL, {"username": "everest"})
    assert resp.status_code == 200
    data = _data(resp)
    assert data["available"] is True
    assert data["suggestions"] == []


def test_taken_username_returns_suggestions(api, make_user):
    services.provision_workspace(
        owner=make_user(role="OWNER"), hostel_name="Everest",
        workspace_username="everest",
    )
    data = _data(api.get(AVAIL, {"username": "everest"}))
    assert data["available"] is False
    assert data["reason"] == "taken"
    assert data["suggestions"]
    assert "everest" not in data["suggestions"]


def test_reserved_username_unavailable(api, db):
    data = _data(api.get(AVAIL, {"username": "admin"}))
    assert data["available"] is False
    assert data["reason"] == "reserved"


def test_invalid_username_unavailable_with_reason(api, db):
    data = _data(api.get(AVAIL, {"username": "ever est@"}))
    assert data["available"] is False
    assert data["reason"] == "invalid"
    assert data["suggestions"]  # still helps the user forward


def test_availability_normalizes_input(api, db):
    data = _data(api.get(AVAIL, {"username": "  EVEREST  "}))
    assert data["username"] == "everest"
    assert data["available"] is True


# --- Registration ------------------------------------------------------------
def test_register_workspace(auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    resp = client.post(WORKSPACES, {
        "hostel_name": "Himalayan Hostel",
        "workspace_username": "himalayan",
    })
    assert resp.status_code == 201, resp.content
    data = _data(resp)
    assert data["slug"] == "himalayan"
    assert data["status"] == WorkspaceStatus.TRIAL
    assert "himalayan" in data["workspace_url"]
    ws = Hostel.objects.get(slug="himalayan")
    assert ws.owner == owner


def test_register_duplicate_username_rejected(auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    assert client.post(WORKSPACES, {
        "hostel_name": "A", "workspace_username": "sunrise"}).status_code == 201
    assert client.post(WORKSPACES, {
        "hostel_name": "B", "workspace_username": "sunrise"}).status_code == 400


def test_register_reserved_username_rejected(auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    resp = client.post(WORKSPACES, {"hostel_name": "X", "workspace_username": "api"})
    assert resp.status_code == 400


def test_register_requires_auth(api, db):
    assert api.post(WORKSPACES, {"hostel_name": "X"}).status_code == 401


# --- Read / update -----------------------------------------------------------
def test_list_only_my_workspaces(auth_client, owner, hostel, other_hostel):
    client = auth_client(owner, hostel)
    resp = client.get(WORKSPACES)
    data = _data(resp)
    results = data["results"] if isinstance(data, dict) and "results" in data else data
    ids = {w["id"] for w in results}
    assert str(hostel.id) in ids
    assert str(other_hostel.id) not in ids


def test_retrieve_other_tenants_workspace_is_404(auth_client, owner, hostel, other_hostel):
    client = auth_client(owner, hostel)
    assert client.get(f"{WORKSPACES}{other_hostel.id}/").status_code == 404


def test_update_display_fields_but_never_slug(auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    original_slug = hostel.slug
    resp = client.patch(
        f"{WORKSPACES}{hostel.id}/",
        {"name": "Renamed", "slug": "hacked", "currency": "USD"},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    hostel.refresh_from_db()
    assert hostel.name == "Renamed"
    assert hostel.currency == "USD"
    assert hostel.slug == original_slug  # read-only, permanent


def test_non_owner_cannot_update(auth_client, warden, hostel):
    client = auth_client(warden, hostel)
    assert client.patch(
        f"{WORKSPACES}{hostel.id}/", {"name": "Nope"}, format="json"
    ).status_code == 403


def test_current_returns_resolved_workspace(auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    data = _data(client.get(f"{WORKSPACES}current/"))
    assert data["id"] == str(hostel.id)
    assert data["slug"] == hostel.slug


# --- Lifecycle endpoints -----------------------------------------------------
def test_suspend_archive_restore_cycle(auth_client, owner, hostel):
    client = auth_client(owner, hostel)

    assert client.post(f"{WORKSPACES}{hostel.id}/suspend/").status_code == 200
    hostel.refresh_from_db()
    assert hostel.status == WorkspaceStatus.SUSPENDED

    assert client.post(f"{WORKSPACES}{hostel.id}/restore/").status_code == 200
    hostel.refresh_from_db()
    assert hostel.status == WorkspaceStatus.ACTIVE

    assert client.post(f"{WORKSPACES}{hostel.id}/archive/").status_code == 200
    hostel.refresh_from_db()
    assert hostel.status == WorkspaceStatus.ARCHIVED


def test_soft_delete_via_api(auth_client, owner, hostel, other_hostel):
    from apps.accounts.models import UserHostel

    client = auth_client(owner, hostel)
    assert client.delete(f"{WORKSPACES}{hostel.id}/").status_code == 204
    hostel.refresh_from_db()
    assert hostel.is_deleted

    # A token bound to the deleted workspace no longer authenticates...
    assert client.post(f"{WORKSPACES}{hostel.id}/restore/").status_code == 401

    # ...restore works from a session on another workspace the owner belongs to.
    UserHostel.objects.create(user=owner, hostel=other_hostel, is_active=True)
    client2 = auth_client(owner, other_hostel)
    assert client2.post(f"{WORKSPACES}{hostel.id}/restore/").status_code == 200
    hostel.refresh_from_db()
    assert not hostel.is_deleted


def test_lifecycle_requires_owner_role(auth_client, warden, hostel):
    client = auth_client(warden, hostel)
    assert client.post(f"{WORKSPACES}{hostel.id}/suspend/").status_code == 403
    assert client.delete(f"{WORKSPACES}{hostel.id}/").status_code == 403


# --- Cross-tenant isolation (end-to-end) --------------------------------------
def test_scoped_endpoint_never_leaks_other_tenant(auth_client, make_user, hostel, other_hostel):
    """A member of hostel A presenting workspace B's identifier must never see
    B's data. Since Prompt 02, tokens are hard-bound to their workspace: the
    mismatched request is rejected outright (401) — stronger than the old
    behaviour of silently re-scoping to A."""
    from apps.residents.models import Resident

    Resident.objects.create(
        hostel=other_hostel, full_name="Bob Theirs", phone="9800000002", monthly_fee=5000
    )

    user = make_user(role="WARDEN", hostel=hostel)
    client = auth_client(user, hostel)
    resp = client.get("/api/residents/", HTTP_X_WORKSPACE=other_hostel.slug)
    assert resp.status_code == 401
    assert b"Bob Theirs" not in resp.content

    # Same token against its OWN workspace keeps working.
    assert client.get("/api/residents/", HTTP_X_WORKSPACE=hostel.slug).status_code == 200


def test_anonymous_cannot_probe_suspended_workspace(api, hostel):
    services.suspend_workspace(hostel)
    resp = api.get("/api/residents/", HTTP_X_WORKSPACE=hostel.slug)
    assert resp.status_code == 403
