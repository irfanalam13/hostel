"""Workspace Management (Prompt 04): overview, namespaced settings, rename +
301 aliases, team management, activity logs, danger zone, preference
integration with the public website, and tenant isolation."""
import pytest
from django.test import override_settings

from apps.tenants import services
from apps.tenants.models import WorkspaceAlias

pytestmark = pytest.mark.django_db

OVERVIEW = "/api/tenants/manage/overview/"
SETTINGS_NS = "/api/tenants/manage/settings/{ns}/"
RENAME = "/api/tenants/manage/rename/"
ACTIVITY = "/api/tenants/manage/activity/"
TEAM = "/api/tenants/manage/team/"
DANGER = "/api/tenants/manage/danger/{action}/"
EXPORT = "/api/tenants/manage/export/"
PUBLIC_SITE = "/api/website/public/"

PASSWORD = "TestPass!234"  # conftest make_user default


def _data(resp):
    body = resp.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


# --- Overview ------------------------------------------------------------------
def test_overview_reports_identity_counts_and_subscription(auth_client, owner, make_user, hostel):
    make_user(role="STUDENT", hostel=hostel)
    make_user(role="PARENT", hostel=hostel)
    make_user(role="WARDEN", hostel=hostel)

    data = _data(auth_client(owner, hostel).get(OVERVIEW))
    assert data["workspace"]["slug"] == hostel.slug
    assert data["counts"]["students"] == 1
    assert data["counts"]["parents"] == 1
    assert data["counts"]["staff"] >= 2  # warden + owner
    assert data["subscription"]["plan"] == hostel.plan_name
    assert "storage_bytes" in data


# --- Namespaced settings ----------------------------------------------------------
def test_profile_settings_roundtrip(auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    resp = client.get(SETTINGS_NS.format(ns="profile"))
    assert resp.status_code == 200
    assert _data(resp)["settings"]["legal_name"] == ""

    resp = client.patch(SETTINGS_NS.format(ns="profile"), {
        "legal_name": "Everest Hostel Pvt. Ltd.",
        "established_year": 2015,
        "social_links": {"facebook": "https://fb.com/everest"},
    }, format="json")
    assert resp.status_code == 200, resp.content
    settings_out = _data(resp)["settings"]
    assert settings_out["legal_name"] == "Everest Hostel Pvt. Ltd."
    assert settings_out["established_year"] == 2015
    # Nested merge: untouched social keys keep defaults.
    assert settings_out["social_links"]["facebook"] == "https://fb.com/everest"
    assert settings_out["social_links"]["instagram"] == ""


def test_settings_validation_rejects_unknown_and_bad_types(auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    assert client.patch(SETTINGS_NS.format(ns="profile"),
                        {"hacker_field": "x"}, format="json").status_code == 400
    assert client.patch(SETTINGS_NS.format(ns="security"),
                        {"max_login_attempts": "many"}, format="json").status_code == 400
    assert client.get(SETTINGS_NS.format(ns="nope")).status_code == 400


def test_profile_edit_never_touches_username_or_url(auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    slug = hostel.slug
    client.patch(SETTINGS_NS.format(ns="profile"), {"legal_name": "New Legal"}, format="json")
    hostel.refresh_from_db()
    assert hostel.slug == slug


def test_settings_writes_require_manage_permission(auth_client, make_user, hostel):
    warden = make_user(role="WARDEN", hostel=hostel)
    client = auth_client(warden, hostel)
    # WARDEN has no workspace.view/manage -> read and write both denied.
    assert client.get(SETTINGS_NS.format(ns="profile")).status_code == 403
    assert client.patch(SETTINGS_NS.format(ns="profile"),
                        {"legal_name": "X"}, format="json").status_code == 403


def test_settings_are_tenant_isolated(auth_client, make_user, hostel, other_hostel):
    owner_a = make_user(role="OWNER", hostel=hostel)
    owner_b = make_user(role="OWNER", hostel=other_hostel)
    auth_client(owner_a, hostel).patch(
        SETTINGS_NS.format(ns="profile"), {"legal_name": "A Legal"}, format="json")
    data_b = _data(auth_client(owner_b, other_hostel).get(SETTINGS_NS.format(ns="profile")))
    assert data_b["settings"]["legal_name"] == ""  # B never sees A's config


# --- Rename + aliases ---------------------------------------------------------------
@override_settings(TENANT_BASE_DOMAIN="myhostel.com", ALLOWED_HOSTS=["*"])
def test_rename_changes_url_and_creates_permanent_redirect(api, auth_client, make_user, hostel):
    owner = make_user(role="OWNER", hostel=hostel, password=PASSWORD)
    client = auth_client(owner, hostel)
    old_slug = hostel.slug

    resp = client.post(RENAME, {
        "workspace_username": "everestgroup", "password": PASSWORD,
    }, format="json")
    assert resp.status_code == 200, resp.content
    hostel.refresh_from_db()
    assert hostel.slug == "everestgroup"
    assert WorkspaceAlias.objects.filter(slug=old_slug, hostel=hostel).exists()

    # New URL resolves…
    assert api.get("/api/website/public/", HTTP_X_WORKSPACE="everestgroup").status_code == 200
    # …old URL answers with a permanent redirect to the new workspace.
    moved = api.get("/api/residents/", HTTP_HOST=f"{old_slug}.myhostel.com")
    assert moved.status_code == 301
    assert "everestgroup.myhostel.com" in moved["Location"]
    assert moved["X-Workspace-Moved-To"] == "everestgroup"


def test_rename_requires_password_and_owner(auth_client, make_user, hostel):
    owner = make_user(role="OWNER", hostel=hostel, password=PASSWORD)
    client = auth_client(owner, hostel)
    assert client.post(RENAME, {"workspace_username": "newname"},
                       format="json").status_code == 400  # no password
    assert client.post(RENAME, {"workspace_username": "newname", "password": "wrong"},
                       format="json").status_code == 400

    manager = make_user(role="MANAGER", hostel=hostel, password=PASSWORD)
    assert auth_client(manager, hostel).post(
        RENAME, {"workspace_username": "newname", "password": PASSWORD},
        format="json").status_code == 403


def test_retired_username_cannot_be_claimed_by_another_workspace(
    auth_client, make_user, hostel, other_hostel,
):
    owner = make_user(role="OWNER", hostel=hostel, password=PASSWORD)
    old_slug = hostel.slug
    auth_client(owner, hostel).post(
        RENAME, {"workspace_username": "brandnew", "password": PASSWORD}, format="json")

    # Availability says taken; registration under the old name is impossible.
    assert not services.is_workspace_username_available(old_slug)
    owner_b = make_user(role="OWNER", hostel=other_hostel, password=PASSWORD)
    resp = auth_client(owner_b, other_hostel).post(
        "/api/tenants/workspaces/",
        {"hostel_name": "Squatter", "workspace_username": old_slug}, format="json")
    assert resp.status_code == 400


def test_rename_back_reclaims_own_alias(auth_client, make_user, hostel):
    owner = make_user(role="OWNER", hostel=hostel, password=PASSWORD)
    client = auth_client(owner, hostel)
    original = hostel.slug
    client.post(RENAME, {"workspace_username": "temporary-name", "password": PASSWORD},
                format="json")
    resp = client.post(RENAME, {"workspace_username": original, "password": PASSWORD},
                       format="json")
    assert resp.status_code == 200, resp.content
    hostel.refresh_from_db()
    assert hostel.slug == original
    # The reclaimed name is no longer an alias; the temporary one now is.
    assert not WorkspaceAlias.objects.filter(slug=original).exists()
    assert WorkspaceAlias.objects.filter(slug="temporary-name", hostel=hostel).exists()


# --- Team management -----------------------------------------------------------------
def test_team_invite_list_role_change_and_removal(auth_client, owner, hostel):
    client = auth_client(owner, hostel)

    resp = client.post(TEAM, {
        "username": "new-warden", "email": "warden@example.com", "role": "WARDEN",
    }, format="json")
    assert resp.status_code == 201, resp.content
    invited = _data(resp)
    assert invited["temporary_password"]

    members = _data(client.get(TEAM))
    entry = next(m for m in members if m["username"] == "new-warden")
    assert entry["role"] == "WARDEN"
    assert entry["is_owner"] is False

    # Role change
    resp = client.patch(f"{TEAM}{entry['user_id']}/", {"role": "MANAGER"}, format="json")
    assert resp.status_code == 200
    # Removal
    assert client.delete(f"{TEAM}{entry['user_id']}/").status_code == 204
    assert all(m["username"] != "new-warden" for m in _data(client.get(TEAM)))


def test_team_guards(auth_client, owner, make_user, hostel):
    client = auth_client(owner, hostel)
    assert client.post(TEAM, {"username": "x", "role": "OWNER"},
                       format="json").status_code == 400  # can't invite an owner
    # Can't remove or role-change yourself.
    assert client.delete(f"{TEAM}{owner.id}/").status_code == 400
    assert client.patch(f"{TEAM}{owner.id}/", {"role": "STAFF"}, format="json").status_code == 400
    # Staff can't manage the team at all.
    staff = make_user(role="STAFF", hostel=hostel)
    assert auth_client(staff, hostel).get(TEAM).status_code == 403


def test_invited_user_belongs_only_to_this_workspace(auth_client, owner, make_user,
                                                     hostel, other_hostel):
    auth_client(owner, hostel).post(TEAM, {"username": "scoped-user", "role": "STAFF"},
                                    format="json")
    owner_b = make_user(role="OWNER", hostel=other_hostel)
    members_b = _data(auth_client(owner_b, other_hostel).get(TEAM))
    assert all(m["username"] != "scoped-user" for m in members_b)


# --- Activity logs ---------------------------------------------------------------------
def test_activity_log_scoped_and_filterable(auth_client, make_user, hostel, other_hostel):
    owner_a = make_user(role="OWNER", hostel=hostel)
    owner_b = make_user(role="OWNER", hostel=other_hostel)
    client_a = auth_client(owner_a, hostel)

    client_a.patch(SETTINGS_NS.format(ns="profile"), {"legal_name": "A"}, format="json")
    auth_client(owner_b, other_hostel).patch(
        SETTINGS_NS.format(ns="profile"), {"legal_name": "B"}, format="json")

    events = _data(client_a.get(ACTIVITY))
    assert any("profile settings updated" in e["message"] for e in events)
    # Strictly this workspace's trail.
    assert all(e["actor"] != owner_b.username for e in events)

    filtered = _data(client_a.get(ACTIVITY, {"q": "profile"}))
    assert filtered and all("profile" in (e["message"] + e["entity_type"]).lower()
                            for e in filtered)


# --- Danger zone -----------------------------------------------------------------------
def test_danger_zone_requires_password(auth_client, make_user, hostel):
    owner = make_user(role="OWNER", hostel=hostel, password=PASSWORD)
    client = auth_client(owner, hostel)
    assert client.post(DANGER.format(action="reset_branding"), {}, format="json").status_code == 400
    resp = client.post(DANGER.format(action="reset_branding"),
                       {"password": PASSWORD}, format="json")
    assert resp.status_code == 200


def test_danger_disable_website(api, auth_client, make_user, hostel):
    owner = make_user(role="OWNER", hostel=hostel, password=PASSWORD)
    client = auth_client(owner, hostel)
    api.get(PUBLIC_SITE, HTTP_X_WORKSPACE=hostel.slug)  # scaffold + publish
    resp = client.post(DANGER.format(action="disable_website"),
                       {"password": PASSWORD}, format="json")
    assert resp.status_code == 200
    assert api.get(PUBLIC_SITE, HTTP_X_WORKSPACE=hostel.slug).status_code == 404


def test_settings_export_import_roundtrip(auth_client, make_user, hostel, other_hostel):
    owner_a = make_user(role="OWNER", hostel=hostel, password=PASSWORD)
    client_a = auth_client(owner_a, hostel)
    client_a.patch(SETTINGS_NS.format(ns="regional"), {"currency": "USD"}, format="json")

    exported = _data(client_a.get(EXPORT))
    assert exported["settings"]["regional"]["currency"] == "USD"

    owner_b = make_user(role="OWNER", hostel=other_hostel, password=PASSWORD)
    client_b = auth_client(owner_b, other_hostel)
    resp = client_b.post(EXPORT, {
        "password": PASSWORD, "settings": {"regional": {"currency": "USD"}},
    }, format="json")
    assert resp.status_code == 200
    data_b = _data(client_b.get(SETTINGS_NS.format(ns="regional")))
    assert data_b["settings"]["currency"] == "USD"


# --- Preference integration with the public website (Prompt 03) --------------------------
def test_disable_public_website_preference(api, auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    assert api.get(PUBLIC_SITE, HTTP_X_WORKSPACE=hostel.slug).status_code == 200
    client.patch(SETTINGS_NS.format(ns="preferences"),
                 {"enable_public_website": False}, format="json")
    assert api.get(PUBLIC_SITE, HTTP_X_WORKSPACE=hostel.slug).status_code == 404


def test_disable_inquiry_preference(api, auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    client.patch(SETTINGS_NS.format(ns="preferences"),
                 {"enable_online_inquiry": False}, format="json")
    resp = api.post("/api/website/public/inquiries/", {
        "name": "Ram", "phone": "980", "message": "Hello there, any rooms?",
    }, HTTP_X_WORKSPACE=hostel.slug)
    assert resp.status_code == 403
    # The published payload also hides the form.
    site = _data(api.get(PUBLIC_SITE, HTTP_X_WORKSPACE=hostel.slug))
    contact = next(s for s in site["sections"] if s["type"] == "contact")
    assert contact["content"]["show_inquiry_form"] is False


def test_disable_gallery_preference_hides_section(api, auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    api.get(PUBLIC_SITE, HTTP_X_WORKSPACE=hostel.slug)  # scaffold
    client.patch(SETTINGS_NS.format(ns="preferences"),
                 {"enable_gallery": False}, format="json")
    site = _data(api.get(PUBLIC_SITE, HTTP_X_WORKSPACE=hostel.slug))
    assert "gallery" not in [s["type"] for s in site["sections"]]


# --- Branding propagation ---------------------------------------------------------------
def test_workspace_branding_reaches_login_branding_endpoint(api, auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    client.patch(SETTINGS_NS.format(ns="branding"),
                 {"logo": "https://cdn.example/logo.png",
                  "login_background": "https://cdn.example/bg.jpg"}, format="json")
    data = _data(api.get("/api/tenants/workspaces/public/", HTTP_X_WORKSPACE=hostel.slug))
    assert data["logo"] == "https://cdn.example/logo.png"
    assert data["login_background"] == "https://cdn.example/bg.jpg"