"""End-to-end consumer (reviewer) signup + login via HTTP — the OTP-verified
signup flow, the hidden platform-workspace linkage, and the login path."""
import pytest

from apps.accounts.models import SignupOTP, User, UserHostel
from apps.discovery.models import ConsumerProfile
from apps.tenants.services import get_or_create_platform_workspace

pytestmark = pytest.mark.django_db

SIGNUP_URL = "/api/auth/consumer/signup/"
LOGIN_URL = "/api/auth/consumer/login/"


def _signup_payload(**overrides):
    payload = {
        "email": "reviewer@example.com",
        "otp": "123456",
        "password": "StrongPass!234",
        "password2": "StrongPass!234",
        "full_name": "Aashish Karki",
        "phone": "9800011122",
    }
    payload.update(overrides)
    return payload


def test_signup_requires_a_valid_otp(api):
    resp = api.post(SIGNUP_URL, _signup_payload())
    assert resp.status_code == 400
    assert not User.objects.filter(email="reviewer@example.com").exists()


def test_successful_signup_creates_consumer_account_and_session(api):
    SignupOTP.objects.create(email="reviewer@example.com", otp="123456")

    resp = api.post(SIGNUP_URL, _signup_payload())
    assert resp.status_code == 201, resp.content

    user = User.objects.get(email="reviewer@example.com")
    assert user.role == "CONSUMER"
    profile = ConsumerProfile.objects.get(user=user)
    assert profile.phone == "9800011122"
    assert profile.full_name == "Aashish Karki"

    platform = get_or_create_platform_workspace()
    assert UserHostel.objects.filter(user=user, hostel=platform, is_active=True).exists()

    # Session cookies were set (cookie-based JWT).
    assert "hostel_access" in resp.cookies or any("access" in k.lower() for k in resp.cookies)


def test_signup_otp_cannot_be_replayed(api):
    SignupOTP.objects.create(email="reviewer@example.com", otp="123456")
    first = api.post(SIGNUP_URL, _signup_payload())
    assert first.status_code == 201

    second = api.post(SIGNUP_URL, _signup_payload(email="another@example.com"))
    assert second.status_code == 400


def test_duplicate_email_signup_rejected(api, make_user):
    make_user(role="CONSUMER", username="existing", email="reviewer@example.com")
    SignupOTP.objects.create(email="reviewer@example.com", otp="123456")

    resp = api.post(SIGNUP_URL, _signup_payload())
    assert resp.status_code == 400


def test_login_after_signup(api):
    SignupOTP.objects.create(email="reviewer@example.com", otp="123456")
    api.post(SIGNUP_URL, _signup_payload())

    resp = api.post(LOGIN_URL, {"email": "reviewer@example.com", "password": "StrongPass!234"})
    assert resp.status_code == 200, resp.content
    assert resp.json()["role"] == "CONSUMER"


def test_login_rejects_wrong_password(api):
    SignupOTP.objects.create(email="reviewer@example.com", otp="123456")
    api.post(SIGNUP_URL, _signup_payload())

    resp = api.post(LOGIN_URL, {"email": "reviewer@example.com", "password": "WrongPass!234"})
    assert resp.status_code == 400


def test_staff_account_cannot_use_consumer_login(api, make_user):
    make_user(role="OWNER", email="owner@example.com", password="StrongPass!234")
    resp = api.post(LOGIN_URL, {"email": "owner@example.com", "password": "StrongPass!234"})
    assert resp.status_code == 400
