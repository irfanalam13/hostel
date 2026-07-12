"""Behaviour-driven IP reputation.

Every security violation (rate limit, WAF hit, bot block, auth failure, …)
adds configurable penalty points to the source IP. The score decays
automatically (Redis TTL), so reputation is *temporary* by default —
persistent good behaviour recovers an address without operator action.
Permanent verdicts belong in ``IPRule`` (allow/deny/trust), which the
middleware consults before reputation.

Thresholds (all configurable, hot-reloadable):

* ``suspicious_threshold`` — logged, available to later layers as a signal.
* ``block_threshold``      — a hard block marker is set for
  ``block_seconds``; the middleware rejects the address outright. The score
  keeps decaying, so blocks self-heal (automatic recovery).

State lives in Redis (shared by all containers). Without Redis the system
degrades to "no reputation" — the rate limiters still protect each process.
"""
import logging

from . import redis_client
from .conf import get_config

logger = logging.getLogger("apps.security")

_SCORE_KEY = "sec:rep:score:{ip}"
_BLOCK_KEY = "sec:rep:block:{ip}"

STATUS_OK = "ok"
STATUS_SUSPICIOUS = "suspicious"
STATUS_BLOCKED = "blocked"

# Atomic: bump score, refresh decay TTL, set block marker at threshold.
_PENALIZE_LUA = """
local score = redis.call('INCRBY', KEYS[1], ARGV[1])
redis.call('EXPIRE', KEYS[1], ARGV[2])
if score >= tonumber(ARGV[3]) then
  redis.call('SET', KEYS[2], score, 'EX', ARGV[4])
end
return score
"""


def _conf():
    return get_config().get("reputation") or {}


def penalize(ip: str, reason: str, points: int | None = None) -> int:
    """Add penalty points for ``reason`` (a key under reputation.penalties,
    or explicit ``points``). Returns the new score (0 if disabled/degraded)."""
    conf = _conf()
    if not conf.get("enabled", True):
        return 0
    client = redis_client.get_client()
    if client is None:
        return 0
    pts = points if points is not None else int((conf.get("penalties") or {}).get(reason, 1))
    try:
        score = int(client.eval(
            _PENALIZE_LUA, 2,
            _SCORE_KEY.format(ip=ip), _BLOCK_KEY.format(ip=ip),
            pts,
            int(conf.get("decay_seconds", 3600)),
            int(conf.get("block_threshold", 50)),
            int(conf.get("block_seconds", 3600)),
        ))
        if score >= int(conf.get("block_threshold", 50)):
            logger.warning("ip reputation BLOCK ip=%s score=%s reason=%s", ip, score, reason)
        return score
    except Exception:
        redis_client.mark_down()
        return 0


def status(ip: str) -> tuple[str, int]:
    """(STATUS_*, score) for an address. Cheap: one pipelined read."""
    conf = _conf()
    if not conf.get("enabled", True):
        return STATUS_OK, 0
    client = redis_client.get_client()
    if client is None:
        return STATUS_OK, 0
    try:
        pipe = client.pipeline(transaction=False)
        pipe.exists(_BLOCK_KEY.format(ip=ip))
        pipe.get(_SCORE_KEY.format(ip=ip))
        blocked, raw = pipe.execute()
        score = int(raw or 0)
        if blocked:
            return STATUS_BLOCKED, score
        if score >= int(conf.get("suspicious_threshold", 20)):
            return STATUS_SUSPICIOUS, score
        return STATUS_OK, score
    except Exception:
        redis_client.mark_down()
        return STATUS_OK, 0


def clear(ip: str) -> None:
    """Operator action: forgive an address immediately."""
    client = redis_client.get_client()
    if client is None:
        return
    try:
        client.delete(_SCORE_KEY.format(ip=ip), _BLOCK_KEY.format(ip=ip))
    except Exception:
        redis_client.mark_down()
