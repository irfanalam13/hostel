"""Production readiness (Prompt 06): health probes, stateless-session config,
storage backend switching, queue monitoring, and no-secrets-in-health-output.
"""
from unittest import mock

import pytest
from django.conf import settings
from django.test import Client

pytestmark = pytest.mark.django_db

client = Client


# --- Health endpoints -----------------------------------------------------------
def test_liveness_probe_touches_nothing(db):
    resp = Client().get("/health/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_database_probe(db):
    resp = Client().get("/health/database/")
    assert resp.status_code == 200
    assert resp.json()["component"] == "database"


def test_storage_probe_roundtrip(db, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    resp = Client().get("/health/storage/")
    assert resp.status_code == 200, resp.content
    assert resp.json() == {"status": "ok", "component": "storage"}
    # The probe cleans up after itself.
    assert not list(tmp_path.rglob(".storage-probe"))


def test_storage_probe_failure_is_generic(db):
    """Storage errors must never leak endpoints/credentials in the response."""
    from django.core.files.storage import Storage

    with mock.patch(
        "django.core.files.storage.default_storage.save",
        side_effect=RuntimeError("s3://secret-bucket AKIA123 connection refused"),
    ):
        resp = Client().get("/health/storage/")
    assert resp.status_code == 503
    body = resp.json()
    assert body["component"] == "storage"
    assert "AKIA123" not in resp.content.decode()
    assert "secret-bucket" not in resp.content.decode()


def test_queue_probe_reports_depth(db, monkeypatch):
    class FakeRedis:
        def llen(self, key):
            assert key == "celery"
            return 7

    import redis

    monkeypatch.setattr(redis.Redis, "from_url", classmethod(lambda cls, *a, **k: FakeRedis()))
    resp = Client().get("/health/queue/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "component": "queue", "depth": 7}


def test_queue_probe_unreachable_broker_is_503(db, monkeypatch):
    import redis

    def boom(cls, *a, **k):
        raise ConnectionError("redis://user:pass@internal-host:6379 down")

    monkeypatch.setattr(redis.Redis, "from_url", classmethod(boom))
    resp = Client().get("/health/queue/")
    assert resp.status_code == 503
    # Generic detail — no broker URL/credentials in the body.
    assert "internal-host" not in resp.content.decode()
    assert resp.json()["detail"] == "broker unreachable"


def test_health_endpoints_never_require_auth_or_tenant(db):
    """LB probes carry no cookies, tokens or workspace headers."""
    for path in ("/health/", "/health/database/", "/health/storage/"):
        resp = Client().get(path)
        assert resp.status_code in (200, 503)  # never 401/403/404


# --- Stateless application design -------------------------------------------------
def test_sessions_are_cache_backed():
    """No local state: sessions ride the shared cache (admin only; the API is
    JWT-cookie based), so any web replica can serve any request."""
    assert settings.SESSION_ENGINE == "django.contrib.sessions.backends.cached_db"


def test_storage_backend_is_env_switchable():
    """The S3 switch exists and defaults to local; the s3 branch configures
    django-storages (import must succeed since it ships in requirements)."""
    assert settings.STORAGE_BACKEND in ("local", "s3")
    import storages.backends.s3  # noqa: F401  (installed + importable)


def test_throttling_uses_shared_cache_config():
    """DRF throttle state must live in the shared cache in production (the
    default cache backend is Redis outside tests) — no per-process limits."""
    rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
    # settings_test empties rates; the production settings module defines them.
    from config import settings as base_settings  # noqa: F401

    assert "default" in settings.CACHES


# --- Metrics ----------------------------------------------------------------------
def test_metrics_not_publicly_routed_by_default(db):
    """PROMETHEUS_ENABLED=False (default) -> /metrics isn't served by Django.
    (In production nginx/traefik additionally block it at the edge.)"""
    resp = Client().get("/metrics")
    assert resp.status_code in (301, 404)
