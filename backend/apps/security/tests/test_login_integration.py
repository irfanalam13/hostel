"""End-to-end auth protection through the real /api/auth/login/ endpoint,
with the security layer enabled and the in-process Redis double."""
import pytest

LOGIN = "/api/auth/login/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(make_user, hostel):
    return make_user(role="WARDEN", hostel=hostel, password="S3cretPass!")


def _payload(user, password):
    hostel = user.hostel_links.get(is_active=True).hostel
    return {"hostel_id": hostel.code, "username": user.username, "password": password}


def test_progressive_lockout_triggers_over_the_endpoint(api, user, install_config, fake_redis):
    # Enforce mode, lock after 3 failures for 60s; generous per-IP throttle so
    # the LOCKOUT (not the blunt throttle) is what trips.
    install_config({
        "auth": {"progressive_lockout": {
            "enabled": True, "scope": "both", "failure_window_seconds": 3600,
            "tiers": [[3, 60]]}},
        "rate_limits": {"auth_login": {"enabled": True, "limit": 50, "window_seconds": 300}},
    })

    statuses = [api.post(LOGIN, _payload(user, "wrong")).status_code for _ in range(5)]
    # First few are ordinary auth rejections; once the tier is crossed the
    # endpoint returns 429 (progressive lockout) — even for more wrong tries.
    assert 429 in statuses
    locked = api.post(LOGIN, _payload(user, "wrong"))
    assert locked.status_code == 429
    assert locked.get("Retry-After") is not None


def test_correct_password_still_works_under_the_limit(api, user, install_config, fake_redis):
    install_config({
        "auth": {"progressive_lockout": {"enabled": True, "scope": "both",
                                         "tiers": [[5, 60]]}},
        "rate_limits": {"auth_login": {"enabled": True, "limit": 50, "window_seconds": 300}},
    })
    # Two failures (tier is 5) must not stop a valid login.
    for _ in range(2):
        api.post(LOGIN, _payload(user, "wrong"))
    ok = api.post(LOGIN, _payload(user, "S3cretPass!"))
    assert ok.status_code == 200


def test_ip_throttle_blocks_login_flood(api, user, install_config, fake_redis):
    # Tight per-IP login throttle, lockout effectively disabled — proves the
    # blunt IP ceiling works independently of progressive lockout.
    install_config({
        "auth": {"progressive_lockout": {"enabled": False}},
        "rate_limits": {"auth_login": {"enabled": True, "algorithm": "sliding_window",
                                       "limit": 3, "window_seconds": 300}},
    })
    statuses = [api.post(LOGIN, _payload(user, "wrong")).status_code for _ in range(6)]
    assert 429 in statuses
