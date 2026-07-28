"""Sign out of all devices (LogoutAllView).

Covered:
  * blacklists every device's refresh token, not just the caller's
  * clears the caller's own cookies
  * requires authentication
  * records an audit event
"""
import pytest
from rest_framework.test import APIClient

from apps.auditlog.models import AuditEvent

LOGIN = "/api/auth/login/"
REFRESH = "/api/auth/token/refresh/"
LOGOUT_ALL = "/api/auth/logout-all/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(make_user, hostel):
    return make_user(role="WARDEN", hostel=hostel, password="S3cretPass!")


def _login(client, hostel, user):
    return client.post(LOGIN, {"hostel_id": hostel.code, "username": user.username, "password": "S3cretPass!"})


def test_logout_all_blacklists_every_device_and_clears_this_ones_cookies(api, user):
    hostel = user.hostel_links.get(is_active=True).hostel
    login_a = _login(api, hostel, user)
    refresh_a = login_a.cookies["refresh_token"].value

    client_b = APIClient()
    login_b = _login(client_b, hostel, user)
    refresh_b = login_b.cookies["refresh_token"].value

    resp = api.post(LOGOUT_ALL)
    assert resp.status_code == 200
    assert resp.data["detail"] == "Signed out of all devices."
    assert resp.cookies["access_token"].value == ""

    fresh = APIClient()
    assert fresh.post(REFRESH, {"refresh": refresh_a}).status_code == 401
    assert fresh.post(REFRESH, {"refresh": refresh_b}).status_code == 401


def test_logout_all_requires_auth(api):
    assert api.post(LOGOUT_ALL).status_code == 401


def test_logout_all_records_audit_event(api, user):
    hostel = user.hostel_links.get(is_active=True).hostel
    _login(api, hostel, user)
    api.post(LOGOUT_ALL)
    assert AuditEvent.objects.filter(
        actor=user,
        action=AuditEvent.Action.LOGOUT,
        message="Signed out of all sessions",
    ).exists()
