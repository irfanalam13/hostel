"""Distributed locking on Redis (single-instance Redlock semantics).

Safety properties:

* **Mutual exclusion** — SET NX with a per-holder random token.
* **Deadlock freedom** — every lock has a TTL; a crashed holder's lock
  auto-releases after ``ttl`` seconds.
* **Safe release / renewal** — release and extend are compare-and-set Lua
  scripts on the holder token, so a lock that expired and was re-acquired by
  someone else can never be released or extended by the old holder.

Usage::

    from apps.security.locks import RedisLock

    with RedisLock("reconcile:hostel:42", ttl=30) as lock:
        if not lock.acquired:
            return  # someone else is doing it
        ...long_running_work()...
        lock.extend()   # renew while still working

When Redis is unavailable the lock reports ``acquired`` per the security
fail strategy (open -> proceed, closed -> don't), so callers need no special
outage handling.
"""
import logging
import time
import uuid

from . import redis_client
from .conf import get_config

logger = logging.getLogger("apps.security")

_RELEASE_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""

_EXTEND_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('PEXPIRE', KEYS[1], ARGV[2])
end
return 0
"""

_PREFIX = "sec:lock:"


class RedisLock:
    def __init__(self, name: str, ttl: float = 30.0,
                 blocking: bool = False, timeout: float = 10.0,
                 retry_interval: float = 0.1):
        """``ttl``: seconds before auto-release. ``blocking``: poll up to
        ``timeout`` seconds for the lock instead of failing fast."""
        self.key = _PREFIX + name
        self.ttl_ms = int(ttl * 1000)
        self.blocking = blocking
        self.timeout = timeout
        self.retry_interval = retry_interval
        self.token = uuid.uuid4().hex
        self.acquired = False

    # ------------------------------------------------------------------ #
    def acquire(self) -> bool:
        client = redis_client.get_client()
        if client is None:
            self.acquired = get_config().fail_open
            if self.acquired:
                logger.warning("RedisLock %s degraded (Redis down, fail-open)", self.key)
            return self.acquired
        deadline = time.monotonic() + self.timeout
        try:
            while True:
                if client.set(self.key, self.token, nx=True, px=self.ttl_ms):
                    self.acquired = True
                    return True
                if not self.blocking or time.monotonic() >= deadline:
                    self.acquired = False
                    return False
                time.sleep(self.retry_interval)
        except Exception:
            redis_client.mark_down()
            self.acquired = get_config().fail_open
            return self.acquired

    def release(self) -> bool:
        if not self.acquired:
            return False
        self.acquired = False
        client = redis_client.get_client()
        if client is None:
            return False
        try:
            return bool(client.eval(_RELEASE_LUA, 1, self.key, self.token))
        except Exception:
            redis_client.mark_down()
            return False  # TTL will reap it — no deadlock

    def extend(self, ttl: float | None = None) -> bool:
        """Renew the lease while still holding the lock (long tasks call this
        periodically — never let a lock silently expire mid-critical-section)."""
        if not self.acquired:
            return False
        client = redis_client.get_client()
        if client is None:
            return False
        try:
            ms = int((ttl or self.ttl_ms / 1000) * 1000)
            return bool(client.eval(_EXTEND_LUA, 1, self.key, self.token, ms))
        except Exception:
            redis_client.mark_down()
            return False

    # ------------------------------------------------------------------ #
    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()
        return False
