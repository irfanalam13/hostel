"""Authentication: login, token refresh, logout, expiry, session reuse.

Covered (Phase 10 §1):
  * login success / invalid password rejection
  * token refresh flow
  * logout invalidation (blacklist) + token reuse after logout
  * expired access token handling
  * invalid token injection
  * multiple concurrent sessions
"""
from datetime import timedelta

import pytest
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

LOGIN = "/api/auth/login/"
REFRESH = "/api/auth/token/refresh/"
LOGOUT = "/api/auth/logout/"
ME = "/api/auth/me/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(make_user, hostel):
    return make_user(role="WARDEN", hostel=hostel, password="S3cretPass!")


# --- login success / failure -----------------------------------------------
def test_login_success_sets_cookies_and_returns_user(api, user):
    resp = api.post(LOGIN, {"username": user.username, "password": "S3cretPass!"})
    assert resp.status_code == 200
    assert resp.data["detail"] == "Login successful"
    assert resp.data["user"]["username"] == user.username
    # httpOnly cookies are set for both tokens.
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies
    assert resp.cookies["access_token"]["httponly"]


def test_login_wrong_password_rejected(api, user):
    resp = api.post(LOGIN, {"username": user.username, "password": "wrong"})
    assert resp.status_code == 401
    assert "access_token" not in resp.cookies


def test_login_unknown_user_rejected(api):
    resp = api.post(LOGIN, {"username": "ghost", "password": "whatever"})
    assert resp.status_code == 401


def test_login_missing_fields_rejected(api, user):
    assert api.post(LOGIN, {"username": user.username}).status_code == 400


# --- token refresh ----------------------------------------------------------
def test_refresh_with_cookie_issues_new_access(api, user):
    login = api.post(LOGIN, {"username": user.username, "password": "S3cretPass!"})
    assert login.status_code == 200
    # The client retains the refresh cookie; refresh should mint a new access.
    resp = api.post(REFRESH)
    assert resp.status_code == 200
    assert resp.data["detail"] == "Token refreshed"
    assert "access_token" in resp.cookies


def test_refresh_without_token_is_unauthorized(api):
    assert api.post(REFRESH).status_code == 401


def test_refresh_with_garbage_token_is_unauthorized(api):
    resp = api.post(REFRESH, {"refresh": "not-a-real-token"})
    assert resp.status_code == 401


# --- logout invalidation / reuse -------------------------------------------
def test_logout_blacklists_refresh_token(api, user):
    from rest_framework.test import APIClient

    refresh = str(RefreshToken.for_user(user))
    # Logging out blacklists this refresh token (passed in the body; the client
    # has no refresh cookie yet so there's no cookie precedence to confuse it).
    assert api.post(LOGOUT, {"refresh": refresh}).status_code == 200
    # Reuse after logout is rejected — use a clean client so no rotated cookie
    # masks the blacklisted token.
    fresh = APIClient()
    assert fresh.post(REFRESH, {"refresh": refresh}).status_code == 401


def test_logout_clears_cookies(api, user):
    api.post(LOGIN, {"username": user.username, "password": "S3cretPass!"})
    resp = api.post(LOGOUT)
    assert resp.status_code == 200
    # Cookies are cleared (expired) on logout.
    assert resp.cookies["access_token"].value == ""


# --- expired / invalid access token ----------------------------------------
def test_expired_access_token_denied(api, user):
    token = AccessToken.for_user(user)
    token.set_exp(lifetime=timedelta(minutes=-5))  # already expired
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    assert api.get(ME).status_code == 401


def test_garbage_access_token_denied(api):
    api.credentials(HTTP_AUTHORIZATION="Bearer garbage.token.value")
    assert api.get(ME).status_code == 401


def test_valid_access_token_reaches_me(api, user):
    token = str(AccessToken.for_user(user))
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    resp = api.get(ME)
    assert resp.status_code == 200
    assert resp.data["username"] == user.username


# --- multiple sessions ------------------------------------------------------
def test_multiple_sessions_both_valid(api, user):
    """Two independent logins both yield working access tokens."""
    t1 = str(AccessToken.for_user(user))
    t2 = str(AccessToken.for_user(user))
    assert t1 != t2
    for tok in (t1, t2):
        client = type(api)()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")
        assert client.get(ME).status_code == 200
