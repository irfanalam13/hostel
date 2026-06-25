"""Health/readiness probes — used by load balancers & deploy gates.

Covered (Phase 10 deployment-safety): liveness, DB readiness, and the 503 path
when a dependency (Redis/Celery) is down. No auth/tenant context required.
"""
import pytest

pytestmark = pytest.mark.django_db


def test_liveness_ok(client):
    resp = client.get("/health/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_database_readiness_ok(client):
    resp = client.get("/health/database/")
    assert resp.status_code == 200
    assert resp.json()["component"] == "database"


def test_cache_readiness_reports_down_when_redis_unreachable(client):
    # Point at an unused port so the ping fails fast -> 503 (the readiness
    # contract the load balancer relies on).
    from django.test import override_settings

    with override_settings(REDIS_URL="redis://127.0.0.1:6390/0"):
        resp = client.get("/health/cache/")
    assert resp.status_code == 503
    assert resp.json()["component"] == "cache"


def test_celery_readiness_reports_down_when_no_workers(client):
    resp = client.get("/health/celery/")
    assert resp.status_code == 503


def test_health_endpoints_reject_post(client):
    assert client.post("/health/").status_code == 405


def test_lockout_response_is_429():
    """The axes lockout callable returns a rendered 429."""
    from apps.accounts.lockout import lockout_response

    resp = lockout_response(request=None)
    assert resp.status_code == 429
    assert b"Too many failed login attempts" in resp.content
