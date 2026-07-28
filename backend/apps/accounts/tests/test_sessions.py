"""Active sessions — list/revoke devices (SessionsView, SessionRevokeView).

Covered:
  * current session is flagged, a second device is not
  * revoking another device blacklists its refresh token
  * revoking your own current session is rejected
  * revoking a missing id, or another user's session id, 404s
  * both endpoints require authentication
"""
import pytest
from rest_framework.test import APIClient

LOGIN = "/api/auth/login/"
REFRESH = "/api/auth/token/refresh/"
SESSIONS = "/api/auth/sessions/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(make_user, hostel):
    return make_user(role="WARDEN", hostel=hostel, password="S3cretPass!")


def _login(client, hostel, username, password="S3cretPass!"):
    return client.post(LOGIN, {"hostel_id": hostel.code, "username": username, "password": password})


def test_sessions_lists_current_session_flagged(api, user):
    hostel = user.hostel_links.get(is_active=True).hostel
    _login(api, hostel, user.username)

    resp = api.get(SESSIONS)
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]["current"] is True
    assert resp.data[0]["device"]


def test_sessions_lists_second_device_not_flagged_current(api, user):
    hostel = user.hostel_links.get(is_active=True).hostel
    _login(api, hostel, user.username)
    client_b = APIClient()
    _login(client_b, hostel, user.username)

    resp = api.get(SESSIONS)
    assert len(resp.data) == 2
    currents = [s["current"] for s in resp.data]
    assert currents.count(True) == 1


def test_session_revoke_signs_out_that_device(api, user):
    hostel = user.hostel_links.get(is_active=True).hostel
    _login(api, hostel, user.username)
    client_b = APIClient()
    login_b = _login(client_b, hostel, user.username)
    refresh_b = login_b.cookies["refresh_token"].value

    other_id = next(s["id"] for s in api.get(SESSIONS).data if not s["current"])
    resp = api.delete(f"{SESSIONS}{other_id}/")
    assert resp.status_code == 200
    assert resp.data["detail"] == "That device has been signed out."

    fresh = APIClient()
    assert fresh.post(REFRESH, {"refresh": refresh_b}).status_code == 401


def test_session_revoke_rejects_own_current_session(api, user):
    hostel = user.hostel_links.get(is_active=True).hostel
    _login(api, hostel, user.username)
    own_id = api.get(SESSIONS).data[0]["id"]

    resp = api.delete(f"{SESSIONS}{own_id}/")
    assert resp.status_code == 400
    assert resp.data["detail"] == "This is your current session — use sign out instead."


def test_session_revoke_not_found_for_missing_id(api, user):
    hostel = user.hostel_links.get(is_active=True).hostel
    _login(api, hostel, user.username)

    resp = api.delete(f"{SESSIONS}999999/")
    assert resp.status_code == 404
    assert resp.data["detail"] == "Session not found."


def test_session_revoke_not_found_for_another_users_token(api, make_user, hostel, user):
    _login(api, hostel, user.username)

    other = make_user(role="WARDEN", hostel=hostel, password="Other!234")
    client2 = APIClient()
    login2 = _login(client2, hostel, other.username, password="Other!234")
    assert login2.status_code == 200
    other_token_id = client2.get(SESSIONS).data[0]["id"]

    resp = api.delete(f"{SESSIONS}{other_token_id}/")
    assert resp.status_code == 404


def test_sessions_requires_auth(api):
    assert api.get(SESSIONS).status_code == 401


def test_session_revoke_requires_auth(api):
    resp = api.delete(f"{SESSIONS}1/")
    assert resp.status_code == 401
