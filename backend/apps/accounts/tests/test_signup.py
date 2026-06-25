"""Signup: creates an OWNER + their hostel, issues a session, validates input.

Covered (Phase 10 §1 + §8 negative cases for the signup payload)."""
import pytest

from apps.accounts.models import User, UserHostel
from apps.tenants.models import Hostel

SIGNUP = "/api/auth/signup/"

pytestmark = pytest.mark.django_db


def _payload(**over):
    data = {
        "username": "newowner",
        "email": "owner@example.com",
        "password": "Str0ng!pass99",
        "password2": "Str0ng!pass99",
        "hostel_name": "Sunrise Hostel",
    }
    data.update(over)
    return data


def test_signup_creates_owner_hostel_and_link(api):
    resp = api.post(SIGNUP, _payload())
    assert resp.status_code == 201
    assert resp.data["detail"] == "Signup successful"
    assert resp.data["hostel_code"]  # returned for the SPA

    user = User.objects.get(username="newowner")
    assert user.role == "OWNER"
    assert user.check_password("Str0ng!pass99")
    hostel = Hostel.objects.get(name="Sunrise Hostel")
    assert UserHostel.objects.filter(user=user, hostel=hostel, is_active=True).exists()
    # Session cookies issued so the new owner is logged straight in.
    assert "access_token" in resp.cookies


def test_signup_password_mismatch_rejected(api):
    resp = api.post(SIGNUP, _payload(password2="Different!99"))
    assert resp.status_code == 400
    assert not User.objects.filter(username="newowner").exists()


def test_signup_weak_password_rejected(api):
    # Too short (<8) and trivial — fails Django's validators.
    resp = api.post(SIGNUP, _payload(password="123", password2="123"))
    assert resp.status_code == 400
    assert not User.objects.filter(username="newowner").exists()


def test_signup_missing_hostel_name_rejected(api):
    data = _payload()
    data.pop("hostel_name")
    assert api.post(SIGNUP, data).status_code == 400


def test_signup_duplicate_username_rejected(api, make_user):
    make_user(username="newowner")
    resp = api.post(SIGNUP, _payload())
    assert resp.status_code == 400
