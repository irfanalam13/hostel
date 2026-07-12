"""Distributed rate-limiting algorithms.

Three enterprise algorithms, each fully atomic (single Lua script on Redis —
correct under any number of app containers) with an equivalent thread-safe
in-memory implementation used as the degraded/dev/test backend:

* **Sliding window log** (ZSET) — *precise*: exactly N requests per rolling
  window, no boundary bursts. Memory is O(limit) per key and every decision is
  one round trip. Default for abuse-facing limits (per-IP, per-tenant) where
  precision beats micro-optimisation.

* **Token bucket** — allows short bursts up to ``capacity`` while enforcing a
  sustained ``refill_rate``/s. O(1) memory. Used for burst smoothing on top of
  the sliding window.

* **Leaky bucket (GCRA)** — constant-rate output with a configurable burst
  tolerance, O(1) memory, no queue to manage (the Generic Cell Rate Algorithm
  is the industry-standard "virtual scheduling" formulation of a leaky
  bucket). Best for expensive downstreams (AI, exports) that want a smooth
  request stream.

All scripts work on Redis Cluster too: each decision touches exactly one key.
"""
import math
import threading
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class Decision:
    """Outcome of one rate-limit evaluation."""

    allowed: bool
    limit: int = 0
    remaining: int = 0
    retry_after: int = 0          # seconds (ceil), 0 when allowed
    scope: str = ""
    algorithm: str = ""
    degraded: bool = False        # True when the fail strategy decided this
    meta: dict = field(default_factory=dict)

    def headers(self, window_seconds: int | None = None) -> dict:
        out = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
        }
        if window_seconds:
            out["X-RateLimit-Reset"] = str(window_seconds)
        if not self.allowed and self.retry_after:
            out["Retry-After"] = str(self.retry_after)
        return out


ALLOW = Decision(allowed=True, degraded=True)


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


# --------------------------------------------------------------------------- #
# Lua scripts — each is atomic and touches a single key (cluster-safe).
# Every script returns {allowed(0/1), remaining, retry_after_ms}.
# --------------------------------------------------------------------------- #
SLIDING_WINDOW_LUA = """
local key    = KEYS[1]
local now    = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit  = tonumber(ARGV[3])
local member = ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local retry = window
  if oldest[2] then
    retry = math.max(1, (tonumber(oldest[2]) + window) - now)
  end
  return {0, 0, retry}
end
redis.call('ZADD', key, now, member)
redis.call('PEXPIRE', key, window + 1000)
return {1, limit - count - 1, 0}
"""

TOKEN_BUCKET_LUA = """
local key      = KEYS[1]
local now      = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local rate     = tonumber(ARGV[3])   -- tokens per millisecond
local cost     = tonumber(ARGV[4])
local data   = redis.call('HMGET', key, 't', 'ts')
local tokens = tonumber(data[1])
local ts     = tonumber(data[2])
if tokens == nil then tokens = capacity end
if ts == nil then ts = now end
tokens = math.min(capacity, tokens + math.max(0, now - ts) * rate)
local allowed = 0
local retry   = 0
if tokens >= cost then
  tokens = tokens - cost
  allowed = 1
else
  retry = math.ceil((cost - tokens) / rate)
end
redis.call('HSET', key, 't', tokens, 'ts', now)
redis.call('PEXPIRE', key, math.ceil(capacity / rate) * 2)
return {allowed, math.floor(tokens), retry}
"""

# GCRA: TAT (theoretical arrival time) stored per key. Allowed while the
# arrival is within the burst tolerance tau of the schedule.
LEAKY_BUCKET_LUA = """
local key      = KEYS[1]
local now      = tonumber(ARGV[1])
local emission = tonumber(ARGV[2])   -- ms between conforming requests
local tau      = tonumber(ARGV[3])   -- burst tolerance in ms
local cost     = tonumber(ARGV[4])
local tat = tonumber(redis.call('GET', key))
if tat == nil or tat < now then tat = now end
local diff = tat - now
if diff > tau then
  return {0, 0, math.ceil(diff - tau)}
end
local new_tat = tat + emission * cost
redis.call('SET', key, new_tat, 'PX', math.ceil(new_tat - now + emission))
local remaining = math.floor((tau - (new_tat - now)) / emission) + 1
if remaining < 0 then remaining = 0 end
return {1, remaining, 0}
"""


class RedisBackend:
    """Runs the Lua scripts against the shared client. Scripts are registered
    once per process (EVALSHA afterwards)."""

    name = "redis"

    def __init__(self, client):
        self.client = client
        self._sliding = client.register_script(SLIDING_WINDOW_LUA)
        self._bucket = client.register_script(TOKEN_BUCKET_LUA)
        self._gcra = client.register_script(LEAKY_BUCKET_LUA)

    def sliding_window(self, key, limit, window_ms, cost=1):
        # cost>1 = N distinct members; loop is fine because cost is tiny (1-3).
        result = None
        for _ in range(max(1, int(cost))):
            result = self._sliding(
                keys=[key], args=[_now_ms(), window_ms, limit, uuid.uuid4().hex]
            )
            if not result[0]:
                break
        return int(result[0]), int(result[1]), int(result[2])

    def token_bucket(self, key, capacity, refill_per_sec, cost=1):
        rate_ms = max(refill_per_sec, 0.001) / 1000.0
        result = self._bucket(keys=[key], args=[_now_ms(), capacity, rate_ms, cost])
        return int(result[0]), int(result[1]), int(result[2])

    def leaky_bucket(self, key, emission_ms, tau_ms, cost=1):
        result = self._gcra(keys=[key], args=[_now_ms(), emission_ms, tau_ms, cost])
        return int(result[0]), int(result[1]), int(result[2])


class MemoryBackend:
    """Per-process fallback with identical semantics. Correct for a single
    container; across replicas it under-counts (each container has its own
    budget) — that is the documented degraded mode when Redis is down and the
    fail strategy is 'open'. Also the deterministic backend for tests."""

    name = "memory"
    _MAX_KEYS = 50_000  # hard bound so an attacker can't exhaust process memory

    def __init__(self):
        self._lock = threading.Lock()
        self._windows: dict[str, list] = {}
        self._buckets: dict[str, tuple] = {}
        self._tats: dict[str, float] = {}

    def _evict_if_needed(self, store):
        if len(store) > self._MAX_KEYS:
            for stale in list(store.keys())[: self._MAX_KEYS // 10]:
                store.pop(stale, None)

    def sliding_window(self, key, limit, window_ms, cost=1):
        now = _now_ms()
        with self._lock:
            self._evict_if_needed(self._windows)
            events = [ts for ts in self._windows.get(key, []) if ts > now - window_ms]
            if len(events) + cost > limit:
                retry = int((events[0] + window_ms) - now) if events else window_ms
                self._windows[key] = events
                return 0, max(0, limit - len(events)), max(1, retry)
            events.extend([now] * cost)
            self._windows[key] = events
            return 1, limit - len(events), 0

    def token_bucket(self, key, capacity, refill_per_sec, cost=1):
        now = _now_ms()
        rate_ms = max(refill_per_sec, 0.001) / 1000.0
        with self._lock:
            self._evict_if_needed(self._buckets)
            tokens, ts = self._buckets.get(key, (float(capacity), now))
            tokens = min(float(capacity), tokens + max(0, now - ts) * rate_ms)
            if tokens >= cost:
                tokens -= cost
                self._buckets[key] = (tokens, now)
                return 1, int(tokens), 0
            self._buckets[key] = (tokens, now)
            return 0, int(tokens), int(math.ceil((cost - tokens) / rate_ms))

    def leaky_bucket(self, key, emission_ms, tau_ms, cost=1):
        now = _now_ms()
        with self._lock:
            self._evict_if_needed(self._tats)
            tat = max(self._tats.get(key, now), now)
            diff = tat - now
            if diff > tau_ms:
                return 0, 0, int(math.ceil(diff - tau_ms))
            new_tat = tat + emission_ms * cost
            self._tats[key] = new_tat
            remaining = int((tau_ms - (new_tat - now)) // emission_ms) + 1
            return 1, max(0, remaining), 0


def evaluate(backend, key: str, rule: dict, cost: int = 1) -> Decision:
    """Run one rule (a ``rate_limits.*`` config dict) against a backend."""
    algorithm = str(rule.get("algorithm", "sliding_window")).lower()

    if algorithm == "token_bucket":
        capacity = int(rule.get("capacity", 60))
        refill = float(rule.get("refill_rate", 20))
        allowed, remaining, retry_ms = backend.token_bucket(key, capacity, refill, cost)
        limit = capacity
    elif algorithm == "leaky_bucket":
        limit = int(rule.get("limit", 60))
        window_s = int(rule.get("window_seconds", 60))
        burst = int(rule.get("burst", max(1, limit // 10)))
        emission_ms = max(1, int(window_s * 1000 / max(1, limit)))
        allowed, remaining, retry_ms = backend.leaky_bucket(
            key, emission_ms, emission_ms * burst, cost
        )
    else:  # sliding_window (default)
        algorithm = "sliding_window"
        limit = int(rule.get("limit", 60))
        window_ms = int(rule.get("window_seconds", 60)) * 1000
        allowed, remaining, retry_ms = backend.sliding_window(key, limit, window_ms, cost)

    return Decision(
        allowed=bool(allowed),
        limit=limit,
        remaining=remaining,
        retry_after=int(math.ceil(retry_ms / 1000)) if retry_ms else 0,
        algorithm=algorithm,
    )
