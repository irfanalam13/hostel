"""Brute-force protection (django-axes lockout).

Axes is disabled in the default test settings so it doesn't bleed lockout
state across the suite; this module re-enables it locally. The axes signal
receivers are always connected at startup and read ``AXES_ENABLED`` at runtime,
so ``override_settings`` is enough to switch it on for these tests.

Covered (Phase 10 §1 brute-force / rate-limit)."""
import pytest
from django.test import override_settings

LOGIN = "/api/auth/login/"

pytestmark = pytest.mark.django_db

AXES_ON = dict(
    AXES_ENABLED=True,
    AXES_FAILURE_LIMIT=3,
    AXES_RESET_ON_SUCCESS=True,
    AUTHENTICATION_BACKENDS=[
        "axes.backends.AxesStandaloneBackend",
        "django.contrib.auth.backends.ModelBackend",
    ],
)


@pytest.fixture
def user(make_user, hostel):
    return make_user(role="WARDEN", hostel=hostel, password="S3cretPass!")


def login_payload(user, password):
    hostel = user.hostel_links.get(is_active=True).hostel
    return {"hostel_id": hostel.code, "username": user.username, "password": password}


@override_settings(**AXES_ON)
def test_repeated_failures_lock_the_account(api, user):
    from axes.utils import reset

    reset()  # clean slate for this IP/username
    for _ in range(3):
        api.post(LOGIN, login_payload(user, "wrong"))

    # After hitting the failure limit, even the CORRECT password is refused.
    blocked = api.post(LOGIN, login_payload(user, "S3cretPass!"))
    assert blocked.status_code != 200
    assert blocked.status_code in (400, 401, 403, 429)

    # Proof that the refusal is the lockout (not bad credentials): clearing the
    # attempts lets the very same correct password through again.
    reset()
    assert api.post(LOGIN, login_payload(user, "S3cretPass!")).status_code == 200


@override_settings(**AXES_ON)
def test_under_limit_does_not_lock(api, user):
    from axes.utils import reset

    reset()
    # Two failures (limit is 3) must not lock a valid login out.
    for _ in range(2):
        api.post(LOGIN, login_payload(user, "wrong"))
    ok = api.post(LOGIN, login_payload(user, "S3cretPass!"))
    assert ok.status_code == 200
