"""Dedicated Redis client for the distributed limiter.

Separate from Django's cache framework on purpose: the limiter needs raw
atomic Lua scripting, and must be reconfigurable for HA topologies without
touching the app cache:

    SECURITY_REDIS_MODE = standalone (default) | sentinel | cluster
    SECURITY_REDIS_URL              standalone URL (default: REDIS_URL)
    SECURITY_REDIS_SENTINELS        host:port,host:port,...
    SECURITY_REDIS_SENTINEL_MASTER  master set name (default: mymaster)
    SECURITY_REDIS_MAX_CONNECTIONS  pool size per process (default: 50)

Timeouts reuse the app-wide REDIS_CONNECT_TIMEOUT / REDIS_SOCKET_TIMEOUT so a
hung Redis degrades in ~1.5s instead of stalling requests — the engine then
applies the configured fail-open/fail-closed strategy.
"""
import logging
import os
import threading
import time

from django.conf import settings

logger = logging.getLogger("apps.security")

_lock = threading.Lock()
_client = None
_down_until = 0.0  # circuit breaker: don't re-dial a dead Redis on every request

# After a connection failure, treat Redis as down for this many seconds.
_RETRY_SECONDS = float(os.environ.get("SECURITY_REDIS_RETRY_SECONDS", "5"))


def _timeouts() -> dict:
    return {
        "socket_connect_timeout": float(getattr(settings, "REDIS_CONNECT_TIMEOUT", 1.5)),
        "socket_timeout": float(getattr(settings, "REDIS_SOCKET_TIMEOUT", 1.5)),
    }


def _build_client():
    import redis

    mode = os.environ.get("SECURITY_REDIS_MODE", "standalone").strip().lower()
    max_conn = int(os.environ.get("SECURITY_REDIS_MAX_CONNECTIONS", "50"))
    kwargs = {**_timeouts(), "retry_on_timeout": True}

    if mode == "sentinel":
        from redis.sentinel import Sentinel

        raw = os.environ.get("SECURITY_REDIS_SENTINELS", "")
        hosts = []
        for pair in raw.split(","):
            pair = pair.strip()
            if not pair:
                continue
            host, _, port = pair.partition(":")
            hosts.append((host, int(port or 26379)))
        if not hosts:
            raise ValueError("SECURITY_REDIS_MODE=sentinel requires SECURITY_REDIS_SENTINELS")
        master = os.environ.get("SECURITY_REDIS_SENTINEL_MASTER", "mymaster")
        sentinel = Sentinel(hosts, **kwargs)
        return sentinel.master_for(master, max_connections=max_conn, **kwargs)

    if mode == "cluster":
        from redis.cluster import RedisCluster

        url = os.environ.get("SECURITY_REDIS_URL") or getattr(
            settings, "REDIS_URL", "redis://localhost:6379/0"
        )
        return RedisCluster.from_url(url, **kwargs)

    url = os.environ.get("SECURITY_REDIS_URL") or getattr(
        settings, "REDIS_URL", "redis://localhost:6379/0"
    )
    return redis.Redis.from_url(url, max_connections=max_conn, **kwargs)


def get_client():
    """Process-wide pooled client, or None while the circuit breaker is open.
    Callers must treat None / exceptions as 'apply the fail strategy'."""
    global _client, _down_until

    now = time.monotonic()
    if _client is not None:
        return _client
    if now < _down_until:
        return None

    with _lock:
        if _client is not None:
            return _client
        if time.monotonic() < _down_until:
            return None
        try:
            client = _build_client()
            client.ping()
            _client = client
            logger.info("security limiter connected to Redis")
            return _client
        except Exception as exc:
            _down_until = time.monotonic() + _RETRY_SECONDS
            logger.warning("security limiter Redis unavailable (%s) — retry in %.0fs",
                           exc, _RETRY_SECONDS)
            return None


def mark_down() -> None:
    """Called by the engine on a runtime error so subsequent requests skip the
    dead connection until the retry window elapses."""
    global _client, _down_until
    with _lock:
        _client = None
        _down_until = time.monotonic() + _RETRY_SECONDS


def reset_for_tests() -> None:
    global _client, _down_until
    with _lock:
        _client = None
        _down_until = 0.0
