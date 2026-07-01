"""Signup: creates an OWNER + their hostel, issues a session, validates input.

Signup is a two-step, email-verified flow:
  1. POST /api/auth/signup/request-otp/  -> emails a 6-digit code
  2. POST /api/auth/signup/              -> needs that code to create the account

Covered (Phase 10 §1 + §8 negative cases for the signup payload)."""
import pytest
from django.core import mail

from apps.accounts.models import SignupOTP, User, UserHostel
from apps.tenants.models import HOSTEL_CODE_RE, Hostel

SIGNUP = "/api/auth/signup/"
REQUEST_OTP = "/api/auth/signup/request-otp/"

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


def _verified_payload(api, **over):
    """Run step 1 and return a step-2 payload carrying the real OTP."""
    data = _payload(**over)
    assert api.post(REQUEST_OTP, {"email": data["email"]}).status_code == 200
    data["otp"] = (
        SignupOTP.objects.filter(email__iexact=data["email"], is_used=False)
        .latest("created_at")
        .otp
    )
    return data


# --- step 1: request OTP ----------------------------------------------------
def test_request_otp_sends_email(api):
    resp = api.post(REQUEST_OTP, {"email": "owner@example.com"})
    assert resp.status_code == 200
    assert len(mail.outbox) == 1
    assert "verification code" in mail.outbox[0].body.lower()
    assert SignupOTP.objects.filter(email="owner@example.com", is_used=False).exists()


def test_request_otp_requires_valid_email(api):
    assert api.post(REQUEST_OTP, {}).status_code == 400
    assert api.post(REQUEST_OTP, {"email": "not-an-email"}).status_code == 400


# --- step 2: signup ---------------------------------------------------------
def test_signup_creates_owner_hostel_and_link(api):
    resp = api.post(SIGNUP, _verified_payload(api))
    assert resp.status_code == 201
    assert resp.data["detail"] == "Signup successful"
    assert resp.data["hostel_code"]  # returned for the SPA
    assert HOSTEL_CODE_RE.match(resp.data["hostel_code"])

    user = User.objects.get(username="newowner")
    assert user.role == "OWNER"
    assert user.check_password("Str0ng!pass99")
    hostel = Hostel.objects.get(name="Sunrise Hostel")
    assert UserHostel.objects.filter(user=user, hostel=hostel, is_active=True).exists()
    # Session cookies issued so the new owner is logged straight in.
    assert "access_token" in resp.cookies
    # The verification code is burned and can't be replayed.
    assert not SignupOTP.objects.filter(email="owner@example.com", is_used=False).exists()


def test_signup_without_otp_rejected(api):
    # No step 1, no otp field -> rejected, no account created.
    resp = api.post(SIGNUP, _payload())
    assert resp.status_code == 400
    assert not User.objects.filter(username="newowner").exists()


def test_signup_with_wrong_otp_rejected(api):
    api.post(REQUEST_OTP, {"email": "owner@example.com"})
    resp = api.post(SIGNUP, _payload(otp="000000"))
    assert resp.status_code == 400
    assert not User.objects.filter(username="newowner").exists()


def test_signup_otp_cannot_be_reused(api):
    payload = _verified_payload(api)
    assert api.post(SIGNUP, payload).status_code == 201
    # Same code, second account attempt -> rejected.
    resp = api.post(SIGNUP, _payload(username="another", otp=payload["otp"]))
    assert resp.status_code == 400
    assert not User.objects.filter(username="another").exists()


def test_signup_requires_email(api):
    data = _verified_payload(api)
    data.pop("email")
    assert api.post(SIGNUP, data).status_code == 400


def test_signup_password_mismatch_rejected(api):
    resp = api.post(SIGNUP, _verified_payload(api, password2="Different!99"))
    assert resp.status_code == 400
    assert not User.objects.filter(username="newowner").exists()


def test_signup_weak_password_rejected(api):
    # Too short (<8) and trivial — fails Django's validators.
    resp = api.post(SIGNUP, _verified_payload(api, password="123", password2="123"))
    assert resp.status_code == 400
    assert not User.objects.filter(username="newowner").exists()


def test_signup_missing_hostel_name_rejected(api):
    data = _verified_payload(api)
    data.pop("hostel_name")
    assert api.post(SIGNUP, data).status_code == 400


def test_signup_duplicate_username_rejected(api, make_user):
    make_user(username="newowner")
    resp = api.post(SIGNUP, _verified_payload(api))
    assert resp.status_code == 400
