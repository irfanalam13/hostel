"""Regression: the auth handshake must survive a cache (Redis) outage.

Production incident: ``REDIS_URL``/``CACHE_URL`` pointed at an unreachable host,
so ``django.core.cache`` raised on every access. The platform's engine-backed
throttles degrade gracefully, but DRF's built-in ``AnonRateThrottle`` keeps its
history in the Django cache and calls ``cache.get`` directly with no error
handling — so ``GET /api/auth/csrf/`` (AllowAny, so it reaches the throttle
stage) returned 500. The SPA hits ``/auth/csrf/`` before it can do anything, so
signup/login were dead in the wild.

These tests reproduce the outage with a cache backend that raises, and prove the
cache-resilient throttles fail open so the handshake still returns 200.

Note: DRF captures ``THROTTLE_RATES`` and ``throttle_classes`` as class
attributes at import, so we patch them directly rather than via settings. The
throttle's ``cache`` is a live proxy, so ``override_settings(CACHES=...)`` does
reach it.
"""
from unittest import mock

import pytest
from django.core.cache.backends.locmem import LocMemCache
from django.test import override_settings
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

from apps.accounts.views import CSRFView
from apps.security.throttles import ResilientAnonRateThrottle

CSRF = "/api/auth/csrf/"


class ExplodingCache(LocMemCache):
    """Stands in for a Redis backend whose host is unreachable."""

    def get(self, *args, **kwargs):  # noqa: D102
        raise ConnectionError("redis down")

    def set(self, *args, **kwargs):  # noqa: D102
        raise ConnectionError("redis down")

    def incr(self, *args, **kwargs):  # noqa: D102
        raise ConnectionError("redis down")


_EXPLODING = f"{__name__}.ExplodingCache"
_BROKEN_CACHE = {"default": {"BACKEND": _EXPLODING, "LOCATION": "boom"}}
_RATES = {"anon": "60/min", "user": "1000/hour"}


def _rates():
    """Give the built-in throttles a rate (else they no-op before the cache)."""
    return mock.patch.object(SimpleRateThrottle, "THROTTLE_RATES", _RATES)


def test_resilient_anon_throttle_fails_open_when_cache_is_down():
    """Unit: the wrapper swallows the cache error and allows the request."""
    with override_settings(CACHES=_BROKEN_CACHE), _rates():
        allowed = ResilientAnonRateThrottle().allow_request(_FakeRequest(), None)
    assert allowed is True


def test_raw_drf_throttle_still_raises_on_cache_outage():
    """Documents the underlying defect: the built-in throttle does NOT degrade."""
    with override_settings(CACHES=_BROKEN_CACHE), _rates():
        with pytest.raises(ConnectionError):
            AnonRateThrottle().allow_request(_FakeRequest(), None)


@pytest.mark.django_db
def test_csrf_endpoint_returns_200_when_cache_is_down(client):
    """Integration: /auth/csrf/ survives a Redis outage end-to-end."""
    with override_settings(CACHES=_BROKEN_CACHE), _rates(), mock.patch.object(
        CSRFView, "throttle_classes", [ResilientAnonRateThrottle]
    ):
        res = client.get(CSRF)
    assert res.status_code == 200
    assert res.json().get("csrftoken")


@pytest.mark.django_db
def test_csrf_endpoint_500s_with_the_raw_throttle_when_cache_is_down(client):
    """Control: with the un-wrapped throttle the same outage 500s (the bug)."""
    client.raise_request_exception = False  # capture the 500 instead of re-raising
    with override_settings(CACHES=_BROKEN_CACHE), _rates(), mock.patch.object(
        CSRFView, "throttle_classes", [AnonRateThrottle]
    ):
        res = client.get(CSRF)
    assert res.status_code == 500


class _FakeRequest:
    """Minimal request the anon throttle can key off (no auth, stable ident)."""

    method = "GET"
    user = None

    def __init__(self):
        self.META = {"REMOTE_ADDR": "203.0.113.9"}
