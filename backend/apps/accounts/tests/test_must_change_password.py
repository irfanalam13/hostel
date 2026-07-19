"""First-login forced-password-change flag (``User.must_change_password``).

The frontend gate depends on this contract:
  * login + /auth/me expose ``must_change_password``
  * changing the password clears it
so an account provisioned with a temporary/default password is funnelled to the
change-password screen exactly once.
"""
import pytest

LOGIN = "/api/auth/login/"
ME = "/api/auth/me/"
PASSWORD_CHANGE = "/api/auth/password/change/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def flagged_user(make_user, hostel):
    """A member whose account still carries a temporary password."""
    user = make_user(role="STAFF", hostel=hostel, password="TempPass!234")
    user.must_change_password = True
    user.save(update_fields=["must_change_password"])
    return user


def test_login_advertises_must_change_password(api, flagged_user):
    hostel = flagged_user.hostel_links.get(is_active=True).hostel
    resp = api.post(
        LOGIN,
        {"hostel_id": hostel.code, "username": flagged_user.username, "password": "TempPass!234"},
    )
    assert resp.status_code == 200
    # Exposed both as a top-level flag and inside the embedded user object.
    assert resp.data["must_change_password"] is True
    assert resp.data["user"]["must_change_password"] is True


def test_me_exposes_flag_default_false(api, make_user, hostel, auth_client):
    user = make_user(role="WARDEN", hostel=hostel)
    resp = auth_client(user, hostel).get(ME)
    assert resp.status_code == 200
    assert resp.data["must_change_password"] is False


def test_password_change_clears_flag(auth_client, flagged_user):
    hostel = flagged_user.hostel_links.get(is_active=True).hostel
    client = auth_client(flagged_user, hostel)
    resp = client.post(
        PASSWORD_CHANGE,
        {"old_password": "TempPass!234", "new_password": "BrandNew!2345"},
    )
    assert resp.status_code == 200
    flagged_user.refresh_from_db()
    assert flagged_user.must_change_password is False
