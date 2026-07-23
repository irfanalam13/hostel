"""Hermetic fixtures for the security foundation suite.

Every test runs against the deterministic in-memory limiter backend with NO
Redis (redis_client.get_client is forced to None), a fresh engine, and an
explicitly installed config snapshot — no state bleeds between tests and no
external service is required (CI-safe).
"""
import time

import pytest
from django.core.cache import cache
from django.test import override_settings

from apps.security import conf, engine, redis_client
from apps.security.conf import SecurityConfig, _deep_merge
from apps.security.defaults import DEFAULTS


@pytest.fixture(autouse=True)
def _isolate_security(monkeypatch):
    monkeypatch.setattr(redis_client, "get_client", lambda: None)
    conf.reset_for_tests()
    engine.reset_for_tests()
    cache.clear()
    yield
    conf.reset_for_tests()
    engine.reset_for_tests()
    cache.clear()


def make_config(overrides: dict | None = None, ip_rules=None) -> SecurityConfig:
    """A resolved snapshot: DEFAULTS + test baseline (memory backend, enforce,
    no DB persistence) + per-test overrides."""
    import ipaddress

    base = _deep_merge(DEFAULTS, {
        "backend": "memory",
        "mode": "enforce",
        "events": {"persist": False, "persist_async": False},
    })
    data = _deep_merge(base, overrides or {})
    compiled = []
    for cidr, action, tenant_id, rule_id in (ip_rules or []):
        compiled.append((ipaddress.ip_network(cidr, strict=False), action, tenant_id, rule_id))
    return SecurityConfig(data, compiled, generation=1)


@pytest.fixture
def install_config():
    """Install a snapshot as THE process config (what get_config() returns)."""

    def _install(overrides: dict | None = None, ip_rules=None) -> SecurityConfig:
        snapshot = make_config(overrides, ip_rules)
        conf._snapshot = snapshot
        conf._snapshot_gen = snapshot.generation
        conf._last_check = time.monotonic()
        return snapshot

    with override_settings(SECURITY_ENABLED=True, SECURITY_CONFIG_RECHECK_SECONDS=3600):
        yield _install


@pytest.fixture
def fake_redis(monkeypatch):
    """Install the in-process Redis double (see fake_redis.py) so the
    Redis-backed auth modules (progressive lockout, reputation, abuse, replay)
    exercise their real logic hermetically. Applied after the autouse
    None-client patch, so it wins."""
    from .fake_redis import FakeRedis

    client = FakeRedis()
    monkeypatch.setattr(redis_client, "get_client", lambda: client)
    monkeypatch.setattr(redis_client, "mark_down", lambda: None)
    return client
