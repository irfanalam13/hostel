"""Progressive lockout for authentication flows.

Never a fixed block: cumulative failures within a rolling window map to
escalating block durations (config `auth.progressive_lockout.tiers`, e.g.
5→30s, 10→2m, 15→10m, 20→1h, 30→24h). Tracked independently per **IP** and
per **identity** (username+tenant) — the longer active block of the two
applies, so neither a single account nor a single source can be attacked
around the limit.

This complements django-axes (still the primary per-(ip,username) login
lockout). Axes gives a fixed cool-off; this adds the multi-tier escalation,
feeds the CAPTCHA decision, and generalises to OTP/MFA verification — none of
which axes covers.

All state is Redis (shared across containers); a Redis outage degrades to
"no progressive lockout" (axes + IP limits still protect) rather than
failing requests.
"""
import logging

from . import redis_client
from .conf import get_config

logger = logging.getLogger("apps.security")

_FAIL_KEY = "sec:auth:fail:{scope}:{bucket}:{key}"
_BLOCK_KEY = "sec:auth:block:{scope}:{bucket}:{key}"

# Atomic: increment the failure counter, refresh its window, and — when the
# count crosses a tier — set/extend the block marker to that tier's duration.
# Returns {count, block_seconds} (block_seconds 0 = no block set this call).
_FAIL_LUA = """
local count = redis.call('INCRBY', KEYS[1], 1)
redis.call('EXPIRE', KEYS[1], ARGV[1])
local block = 0
local n = tonumber(ARGV[2])
for i = 0, n - 1 do
  local threshold = tonumber(ARGV[3 + i * 2])
  local duration  = tonumber(ARGV[4 + i * 2])
  if count >= threshold then block = duration end
end
if block > 0 then
  redis.call('SET', KEYS[2], count, 'EX', block)
end
return {count, block}
"""


class LockoutState:
    __slots__ = ("locked", "retry_after", "failure_count", "tier", "degraded")

    def __init__(self, locked=False, retry_after=0, failure_count=0,
                 tier=0, degraded=False):
        self.locked = locked
        self.retry_after = retry_after
        self.failure_count = failure_count
        self.tier = tier
        self.degraded = degraded


def _conf():
    return get_config().get("auth.progressive_lockout") or {}


def _buckets(scope: str):
    """Which (bucket) dimensions to track for this scope setting."""
    configured = str(_conf().get("scope", "both")).lower()
    if configured == "ip":
        return ("ip",)
    if configured == "identity":
        return ("identity",)
    return ("ip", "identity")


def _tiers():
    tiers = _conf().get("tiers") or []
    parsed = []
    for entry in tiers:
        try:
            parsed.append((int(entry[0]), int(entry[1])))
        except (TypeError, ValueError, IndexError):
            continue
    return sorted(parsed)


def is_locked(scope: str, ip: str, identity: str) -> LockoutState:
    """Current lockout state for an auth attempt — checked BEFORE verifying
    credentials so a locked caller never even reaches authentication."""
    if not _conf().get("enabled", True):
        return LockoutState()
    client = redis_client.get_client()
    if client is None:
        return LockoutState(degraded=True)

    keys = {"ip": ip, "identity": identity}
    worst = LockoutState()
    try:
        pipe = client.pipeline(transaction=False)
        checked = []
        for bucket in _buckets(scope):
            key = keys.get(bucket) or ""
            if not key:
                continue
            checked.append(bucket)
            pipe.ttl(_BLOCK_KEY.format(scope=scope, bucket=bucket, key=key))
        ttls = pipe.execute()
        for ttl in ttls:
            if ttl and ttl > 0 and ttl > worst.retry_after:
                worst = LockoutState(locked=True, retry_after=int(ttl))
    except Exception:
        redis_client.mark_down()
        return LockoutState(degraded=True)
    return worst


def register_failure(scope: str, ip: str, identity: str) -> LockoutState:
    """Record one failed attempt; return the resulting lockout state (locked +
    retry_after when a tier was crossed)."""
    conf = _conf()
    if not conf.get("enabled", True):
        return LockoutState()
    client = redis_client.get_client()
    if client is None:
        return LockoutState(degraded=True)

    tiers = _tiers()
    if not tiers:
        return LockoutState()
    window = int(conf.get("failure_window_seconds", 3600))
    flat = [v for tier in tiers for v in tier]

    keys = {"ip": ip, "identity": identity}
    result = LockoutState()
    try:
        for bucket in _buckets(scope):
            key = keys.get(bucket) or ""
            if not key:
                continue
            count, block = client.eval(
                _FAIL_LUA, 2,
                _FAIL_KEY.format(scope=scope, bucket=bucket, key=key),
                _BLOCK_KEY.format(scope=scope, bucket=bucket, key=key),
                window, len(tiers), *flat,
            )
            count, block = int(count), int(block)
            if block > 0 and block > result.retry_after:
                result = LockoutState(
                    locked=True, retry_after=block, failure_count=count,
                    tier=sum(1 for t, _ in tiers if count >= t),
                )
            elif count > result.failure_count and not result.locked:
                result.failure_count = count
    except Exception:
        redis_client.mark_down()
        return LockoutState(degraded=True)
    return result


def reset(scope: str, ip: str, identity: str) -> None:
    """Clear counters + blocks after a successful authentication."""
    if not _conf().get("enabled", True):
        return
    client = redis_client.get_client()
    if client is None:
        return
    keys = {"ip": ip, "identity": identity}
    try:
        to_delete = []
        for bucket in ("ip", "identity"):
            key = keys.get(bucket) or ""
            if not key:
                continue
            to_delete.append(_FAIL_KEY.format(scope=scope, bucket=bucket, key=key))
            to_delete.append(_BLOCK_KEY.format(scope=scope, bucket=bucket, key=key))
        if to_delete:
            client.delete(*to_delete)
    except Exception:
        redis_client.mark_down()


def failure_count(scope: str, ip: str, identity: str) -> int:
    """Highest current failure count across the tracked buckets (drives the
    CAPTCHA decision)."""
    client = redis_client.get_client()
    if client is None:
        return 0
    keys = {"ip": ip, "identity": identity}
    highest = 0
    try:
        pipe = client.pipeline(transaction=False)
        buckets = [b for b in _buckets(scope) if keys.get(b)]
        for bucket in buckets:
            pipe.get(_FAIL_KEY.format(scope=scope, bucket=bucket, key=keys[bucket]))
        for raw in pipe.execute():
            highest = max(highest, int(raw or 0))
    except Exception:
        redis_client.mark_down()
        return 0
    return highest
