"""Prompt 02 — tenant-scoped authentication, portals, sessions, RBAC endpoints.

Covers:
  * workspace-context login (X-Workspace header / subdomain) without a Hostel ID
  * cross-tenant login + token-reuse protection
  * portal role gating (student can't enter /admin, etc.) + redirect rules
  * remember-me refresh lifetime
  * password-version (pwv): password change kills other sessions, keeps current
  * workspace-scoped password reset
  * session verify + permission endpoints
  * public workspace branding for login pages
"""
from datetime import timedelta

import pytest
from django.core import mail
from django.test import override_settings

from apps.accounts.models import PasswordResetOTP, User
from apps.accounts.tokens import issue_tokens

LOGIN = "/api/auth/login/"
ME = "/api/auth/me/"
VERIFY = "/api/auth/session/verify/"
PERMISSIONS = "/api/auth/permissions/"
PERM_CHECK = "/api/auth/permissions/check/"
FORGOT = "/api/auth/password/forgot/"
RESET = "/api/auth/password/reset/"
PUBLIC = "/api/tenants/workspaces/public/"

pytestmark = pytest.mark.django_db

PASSWORD = "S3cretPass!"

BASE = override_settings(TENANT_BASE_DOMAIN="myhostel.com", ALLOWED_HOSTS=["*"])


@pytest.fixture
def user(make_user, hostel):
    return make_user(role="WARDEN", hostel=hostel, password=PASSWORD)


def _data(resp):
    body = resp.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


# --- Workspace-context login --------------------------------------------------
def test_login_via_workspace_header_without_hostel_id(api, user, hostel):
    resp = api.post(
        LOGIN,
        {"username": user.username, "password": PASSWORD},
        HTTP_X_WORKSPACE=hostel.slug,
    )
    assert resp.status_code == 200, resp.content
    assert resp.data["workspace"]["username"] == hostel.slug
    assert resp.data["role"] == "WARDEN"
    assert resp.data["redirect"] == "/dashboard"
    assert resp.data["mfa_required"] is False
    assert "access_token" in resp.cookies


@BASE
def test_login_via_subdomain_host(api, user, hostel):
    resp = api.post(
        LOGIN,
        {"username": user.username, "password": PASSWORD},
        HTTP_HOST=f"{hostel.slug}.myhostel.com",
    )
    assert resp.status_code == 200, resp.content
    assert resp.data["workspace"]["username"] == hostel.slug


def test_login_without_any_workspace_context_requires_hostel_id(api, user):
    resp = api.post(LOGIN, {"username": user.username, "password": PASSWORD})
    assert resp.status_code == 400


def test_login_hostel_id_must_match_resolved_workspace(api, user, hostel, other_hostel):
    """Explicit Hostel ID of tenant A while workspace B is resolved -> generic
    failure. Credentials can never open a session in a different workspace."""
    resp = api.post(
        LOGIN,
        {"hostel_id": hostel.code, "username": user.username, "password": PASSWORD},
        HTTP_X_WORKSPACE=other_hostel.slug,
    )
    assert resp.status_code == 400


def test_login_on_workspace_only_finds_that_workspaces_members(api, user, other_hostel):
    """A valid user of workspace A cannot log in on workspace B's host."""
    resp = api.post(
        LOGIN,
        {"username": user.username, "password": PASSWORD},
        HTTP_X_WORKSPACE=other_hostel.slug,
    )
    assert resp.status_code == 400


# --- Portal gating -------------------------------------------------------------
@pytest.mark.parametrize("role,portal,ok", [
    ("OWNER", "admin", True),
    ("OWNER", "staff", True),      # admin roles may use the staff door
    ("ADMIN", "admin", True),
    ("WARDEN", "staff", True),
    ("RECEPTIONIST", "staff", True),
    ("WARDEN", "admin", False),    # staff can never enter the admin portal
    ("STUDENT", "student", True),
    ("RESIDENT", "student", True), # legacy role maps onto the student portal
    ("STUDENT", "admin", False),
    ("STUDENT", "staff", False),
    ("PARENT", "parent", True),
    ("PARENT", "student", False),
    ("READ_ONLY", "staff", True),
])
def test_portal_role_gating(api, make_user, hostel, role, portal, ok):
    u = make_user(role=role, hostel=hostel, password=PASSWORD)
    resp = api.post(
        LOGIN,
        {"username": u.username, "password": PASSWORD, "portal": portal},
        HTTP_X_WORKSPACE=hostel.slug,
    )
    assert (resp.status_code == 200) is ok, resp.content


def test_portal_redirects_by_role(api, make_user, hostel):
    student = make_user(role="STUDENT", hostel=hostel, password=PASSWORD)
    resp = api.post(
        LOGIN,
        {"username": student.username, "password": PASSWORD, "portal": "student"},
        HTTP_X_WORKSPACE=hostel.slug,
    )
    assert resp.data["redirect"] == "/student/dashboard"

    parent = make_user(role="PARENT", hostel=hostel, password=PASSWORD)
    resp = api.post(
        LOGIN,
        {"username": parent.username, "password": PASSWORD, "portal": "parent"},
        HTTP_X_WORKSPACE=hostel.slug,
    )
    assert resp.data["redirect"] == "/parent/dashboard"


# --- Remember me ----------------------------------------------------------------
def test_remember_me_extends_refresh_cookie(api, user, hostel):
    plain = api.post(
        LOGIN, {"username": user.username, "password": PASSWORD},
        HTTP_X_WORKSPACE=hostel.slug,
    )
    from rest_framework.test import APIClient

    remembered = APIClient().post(
        LOGIN, {"username": user.username, "password": PASSWORD, "remember": True},
        HTTP_X_WORKSPACE=hostel.slug,
    )
    plain_age = int(plain.cookies["refresh_token"]["max-age"])
    remembered_age = int(remembered.cookies["refresh_token"]["max-age"])
    assert remembered_age > plain_age
    assert remembered_age == 30 * 24 * 3600  # REMEMBER_ME_REFRESH_DAYS default


# --- Cross-tenant token binding ---------------------------------------------------
def test_token_rejected_on_other_workspace(api, make_user, hostel, other_hostel):
    """A token minted for workspace A must not work against workspace B —
    even for a user who is a member of BOTH workspaces."""
    u = make_user(role="OWNER", hostel=hostel, password=PASSWORD)
    from apps.accounts.models import UserHostel

    UserHostel.objects.create(user=u, hostel=other_hostel, is_active=True)

    _, access = issue_tokens(u, hostel)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    assert api.get(ME, HTTP_X_WORKSPACE=hostel.slug).status_code == 200
    assert api.get(ME, HTTP_X_WORKSPACE=other_hostel.slug).status_code == 401


# --- Password-version invalidation ------------------------------------------------
def test_password_change_invalidates_previous_tokens(api, user, hostel):
    _, old_access = issue_tokens(user, hostel)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {old_access}")
    assert api.get(ME).status_code == 200

    user.set_password("N3wPassword!!")
    user.save(update_fields=["password"])

    assert api.get(ME).status_code == 401  # pwv mismatch -> forced logout


def test_password_change_endpoint_keeps_current_session(api, user, hostel):
    login = api.post(
        LOGIN, {"username": user.username, "password": PASSWORD},
        HTTP_X_WORKSPACE=hostel.slug,
    )
    assert login.status_code == 200

    resp = api.post(
        "/api/auth/password/change/",
        {"old_password": PASSWORD, "new_password": "N3wPassword!!"},
    )
    assert resp.status_code == 200, resp.content
    # Fresh cookies (new pwv) were issued for this device...
    assert "access_token" in resp.cookies
    # ...so the session keeps working after the rotation.
    assert api.get(ME).status_code == 200


def test_legacy_token_without_pwv_still_works(api, user, hostel):
    """Tokens minted before the pwv claim existed stay valid until expiry."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    refresh["hostel_id"] = str(hostel.id)
    refresh["hostel_code"] = hostel.code
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    assert api.get(ME).status_code == 200


# --- Workspace-scoped password recovery -------------------------------------------
def test_password_reset_scoped_to_workspace(api, user, hostel, other_hostel):
    # On the member workspace: OTP email goes out.
    api.post(FORGOT, {"username": user.username}, HTTP_X_WORKSPACE=hostel.slug)
    assert len(mail.outbox) == 1
    assert PasswordResetOTP.objects.filter(user=user, is_used=False).exists()

    # On a workspace the user does NOT belong to: same uniform response, but
    # no OTP and no email — never a global search.
    mail.outbox.clear()
    PasswordResetOTP.objects.all().delete()
    resp = api.post(FORGOT, {"username": user.username}, HTTP_X_WORKSPACE=other_hostel.slug)
    assert resp.status_code == 200  # no enumeration
    assert len(mail.outbox) == 0
    assert not PasswordResetOTP.objects.filter(user=user).exists()


def test_password_reset_confirm_scoped_to_workspace(api, user, hostel, other_hostel):
    otp = PasswordResetOTP.objects.create(user=user, otp="123456")
    resp = api.post(
        RESET,
        {"email_or_username": user.username, "otp": "123456", "new_password": "N3wPassword!!"},
        HTTP_X_WORKSPACE=other_hostel.slug,
    )
    assert resp.status_code == 400  # wrong workspace -> user not found there
    otp.refresh_from_db()
    assert not otp.is_used


# --- Session verify + permissions ----------------------------------------------
def test_session_verify(auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    resp = client.get(VERIFY)
    assert resp.status_code == 200
    assert resp.data["authenticated"] is True
    assert resp.data["role"] == "OWNER"
    assert resp.data["workspace"]["username"] == hostel.slug
    assert resp.data["redirect"] == "/dashboard"


def test_session_verify_requires_auth(api, db):
    assert api.get(VERIFY).status_code == 401


def test_my_permissions_owner_gets_everything(auth_client, owner, hostel):
    resp = auth_client(owner, hostel).get(PERMISSIONS)
    perms = resp.data["permissions"]
    assert "residents.create" in perms
    assert "workspace.manage" in perms
    assert "backups.restore" in perms


def test_my_permissions_student_is_minimal(auth_client, make_user, hostel):
    student = make_user(role="STUDENT", hostel=hostel)
    perms = auth_client(student, hostel).get(PERMISSIONS).data["permissions"]
    assert "billing.view" in perms
    assert "complaints.create" in perms
    assert "residents.create" not in perms
    assert "backups.restore" not in perms


def test_read_only_role_has_only_view_permissions(auth_client, make_user, hostel):
    ro = make_user(role="READ_ONLY", hostel=hostel)
    perms = auth_client(ro, hostel).get(PERMISSIONS).data["permissions"]
    assert perms
    assert all(p.endswith(".view") for p in perms)


def test_permission_check_endpoint(auth_client, warden, make_user, hostel):
    client = auth_client(warden, hostel)
    ok = client.get(PERM_CHECK, {"permission": "residents.create"})
    assert ok.data == {"permission": "residents.create", "allowed": True}
    denied = client.get(PERM_CHECK, {"permission": "backups.restore"})
    assert denied.data["allowed"] is False
    assert client.get(PERM_CHECK).status_code == 400


def test_workspace_permission_override(auth_client, make_user, hostel):
    """Per-workspace RBAC config: a workspace can reshape a role's grants."""
    staff = make_user(role="STAFF", hostel=hostel)
    client = auth_client(staff, hostel)
    assert client.get(PERM_CHECK, {"permission": "billing.view"}).data["allowed"] is False

    hostel.settings = {**(hostel.settings or {}),
                       "permissions": {"roles": {"STAFF": ["billing.*"]}}}
    hostel.save(update_fields=["settings"])  # signal drops the RBAC cache

    assert client.get(PERM_CHECK, {"permission": "billing.view"}).data["allowed"] is True
    assert client.get(PERM_CHECK, {"permission": "residents.view"}).data["allowed"] is False


# --- Public workspace branding ---------------------------------------------------
def test_public_branding_for_resolved_workspace(api, hostel):
    resp = api.get(PUBLIC, HTTP_X_WORKSPACE=hostel.slug)
    assert resp.status_code == 200
    data = _data(resp)
    assert data["name"] == hostel.name
    assert data["workspace_username"] == hostel.slug
    # Never leaks sensitive fields.
    for forbidden in ("owner", "settings", "plan_name", "phone", "code"):
        assert forbidden not in data


def test_public_branding_requires_workspace_context(api, db):
    assert api.get(PUBLIC).status_code == 404


def test_public_branding_blocked_for_suspended_workspace(api, hostel):
    from apps.tenants import services

    services.suspend_workspace(hostel)
    resp = api.get(PUBLIC, HTTP_X_WORKSPACE=hostel.slug)
    assert resp.status_code == 403  # middleware gate: professional error page upstream
