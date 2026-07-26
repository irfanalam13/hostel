"""Super-admin login (`/api/auth/super-admin/login/`) — no Hostel ID, no
portal, separate axis of authority (Django `is_superuser`) from tenant login.

See docs/AUTHENTICATION.md "Super-admin access".
"""
import pytest

from apps.accounts.models import UserHostel
from apps.tenants.services import get_or_create_platform_workspace

LOGIN = "/api/auth/super-admin/login/"

pytestmark = pytest.mark.django_db


def detail_text(resp):
    detail = resp.data["detail"]
    if isinstance(detail, list):
        return str(detail[0])
    return str(detail)


def test_superuser_login_succeeds_and_redirects_to_platform(make_user, api):
    superuser = make_user(username="root", password="Sup3rSecret!", is_superuser=True)

    resp = api.post(LOGIN, {"username": "root", "password": "Sup3rSecret!"})

    assert resp.status_code == 200
    assert resp.data["redirect"] == "/platform"
    assert resp.data["role"] == "SUPER_ADMIN"
    assert resp.data["user"]["id"] == superuser.id
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies

    # The post_save signal auto-linked them to the hidden platform hostel, and
    # its code is surfaced in the response (frontend needs it to avoid
    # ProtectedLayout's "no hostelCode" -> /select-hostel redirect).
    platform_hostel = get_or_create_platform_workspace()
    assert resp.data["hostel_code"] == platform_hostel.code
    assert UserHostel.objects.filter(
        user=superuser, hostel=platform_hostel, is_active=True
    ).exists()


def test_regular_owner_cannot_use_super_admin_login(make_user, hostel, api):
    owner = make_user(role="OWNER", hostel=hostel, password="OwnerPass!234")

    resp = api.post(LOGIN, {"username": owner.username, "password": "OwnerPass!234"})

    # Same generic failure as bad credentials — never reveals "not a superuser".
    assert resp.status_code == 400
    assert detail_text(resp) == "Invalid username or password."


def test_wrong_password_for_superuser_fails(make_user, api):
    make_user(username="root2", password="Sup3rSecret!", is_superuser=True)

    resp = api.post(LOGIN, {"username": "root2", "password": "WrongPassword!"})

    assert resp.status_code == 400
    assert detail_text(resp) == "Invalid username or password."


def test_two_superusers_share_the_same_platform_hostel(make_user, api):
    first = make_user(username="root3", password="Sup3rSecret!", is_superuser=True)
    second = make_user(username="root4", password="Sup3rSecret!", is_superuser=True)

    r1 = api.post(LOGIN, {"username": "root3", "password": "Sup3rSecret!"})
    r2 = api.post(LOGIN, {"username": "root4", "password": "Sup3rSecret!"})

    assert r1.status_code == 200 and r2.status_code == 200

    platform_hostel = get_or_create_platform_workspace()
    assert UserHostel.objects.filter(user=first, hostel=platform_hostel).exists()
    assert UserHostel.objects.filter(user=second, hostel=platform_hostel).exists()
    # Exactly one hidden hostel exists, not one per superuser.
    from apps.tenants.models import Hostel

    assert Hostel.objects.filter(is_platform_workspace=True).count() == 1
