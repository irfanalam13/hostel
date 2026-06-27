"""Password reset: emailed link, no account enumeration, token validation.

Covered (Phase 10 §1 password reset flow)."""
import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

FORGOT = "/api/auth/password/forgot/"
RESET = "/api/auth/password/reset/"
LOGIN = "/api/auth/login/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(make_user, hostel):
    return make_user(
        role="WARDEN", hostel=hostel, password="OldPass!234",
        username="reset_me", email="reset@example.com",
    )


def test_forgot_sends_email_for_existing_account(api, user):
    resp = api.post(FORGOT, {"email": "reset@example.com"})
    assert resp.status_code == 200
    assert len(mail.outbox) == 1
    assert "One-Time Password" in mail.outbox[0].body


def test_forgot_unknown_email_does_not_enumerate(api):
    resp = api.post(FORGOT, {"email": "nobody@example.com"})
    # Same 200 response, but no email is sent — no account enumeration.
    assert resp.status_code == 200
    assert "If the account exists" in resp.data["detail"]
    assert len(mail.outbox) == 0


def test_forgot_requires_email_or_username(api):
    assert api.post(FORGOT, {}).status_code == 400


def test_reset_confirm_changes_password(api, user):
    api.post(FORGOT, {"email": "reset@example.com"})
    otp = user.password_reset_otps.first().otp
    
    resp = api.post(RESET, {"email_or_username": user.email, "otp": otp, "new_password": "BrandNew!99"})
    assert resp.status_code == 200

    user.refresh_from_db()
    assert user.check_password("BrandNew!99")
    # The new password actually works at the login endpoint with the backend-generated Hostel ID.
    hostel_code = user.hostel_links.first().hostel.code
    assert api.post(LOGIN, {"hostel_id": hostel_code, "username": user.username, "password": "BrandNew!99"}).status_code == 200


def test_reset_with_bad_token_rejected(api, user):
    api.post(FORGOT, {"email": "reset@example.com"})
    resp = api.post(RESET, {"email_or_username": user.email, "otp": "000000", "new_password": "BrandNew!99"})
    assert resp.status_code == 400
    user.refresh_from_db()
    assert user.check_password("OldPass!234")  # unchanged


def test_reset_with_bad_uid_rejected(api):
    resp = api.post(RESET, {"email_or_username": "invalid@example.com", "otp": "123456", "new_password": "BrandNew!99"})
    assert resp.status_code == 400


def test_reset_rejects_weak_new_password(api, user):
    api.post(FORGOT, {"email": "reset@example.com"})
    otp = user.password_reset_otps.first().otp
    resp = api.post(RESET, {"email_or_username": user.email, "otp": otp, "new_password": "123"})
    assert resp.status_code == 400


def test_forgot_hostel_id_sends_email(api, user):
    FORGOT_HOSTEL_ID = "/api/auth/hostel-id/forgot/"
    resp = api.post(FORGOT_HOSTEL_ID, {"email_or_username": user.email})
    assert resp.status_code == 200
    assert len(mail.outbox) == 1
    hostel_code = user.hostel_links.first().hostel.code
    assert hostel_code in mail.outbox[0].body
