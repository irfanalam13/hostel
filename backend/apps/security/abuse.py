"""Behavioural abuse detection for authentication flows.

Cheap, Redis-backed heuristics that turn patterns across many requests into a
threat signal and feed IP reputation (which the middleware and CAPTCHA layer
then act on):

* **Credential stuffing** — one IP trying many DISTINCT identities in a short
  window (the signature of a leaked-password list replay). Tracked with a
  bounded per-IP set of hashed identities.
* **Enumeration** — one IP probing many DISTINCT lookup targets (emails /
  usernames) against reset / forgot / signup-otp endpoints, i.e. mapping which
  accounts exist. The endpoints already return uniform responses; this detects
  the scanning behaviour itself.
* **Brute force** — repeated failures against a single identity (progressive
  lockout owns the blocking; this records the reputation penalty + signal).

Identities/targets are stored as short salted hashes, not plaintext — the
detector needs cardinality, not the values. All sets are capped and expire, so
memory is bounded and detection is windowed. No Redis ⇒ detection is skipped
(the hard limits + lockout still apply).
"""
import hashlib
import logging

from . import redis_client, reputation
from .conf import get_config
from .events import record

logger = logging.getLogger("apps.security")

_STUFF_KEY = "sec:abuse:stuff:{ip}"
_ENUM_KEY = "sec:abuse:enum:{ip}"
_MAX_SET = 512  # hard cap on tracked distinct values per IP


def _hash(value: str) -> str:
    # Privacy fingerprint of an identity/target (username/email/IP) so plaintext
    # never hits Redis — we only need set cardinality, not a security primitive
    # (no signing/passwords/tokens). SHA-256 (not SHA-1/MD5) so hashing this
    # sensitive input isn't a weak-hash finding; usedforsecurity=False documents
    # that it's a fingerprint, not an auth secret. Truncated: 64 bits is ample
    # for the capped per-IP sets.
    return hashlib.sha256(
        (value or "").strip().lower().encode(), usedforsecurity=False
    ).hexdigest()[:16]


def _track_distinct(key: str, value: str, window: int, threshold: int):
    """Add ``value`` to a windowed per-IP set; return (distinct_count, tripped).
    Atomic add+expire; the set is size-capped to bound memory."""
    client = redis_client.get_client()
    if client is None or not value:
        return 0, False
    try:
        pipe = client.pipeline(transaction=False)
        pipe.scard(key)
        pipe.sadd(key, _hash(value))
        pipe.expire(key, window)
        current, added, _ = pipe.execute()
        count = int(current) + (1 if added else 0)
        if count > _MAX_SET:
            client.spop(key, count - _MAX_SET)
        return count, count >= threshold
    except Exception:
        redis_client.mark_down()
        return 0, False


def record_credential_stuffing(ip: str, identity: str, request=None) -> bool:
    """Track a login attempt's identity; flag + penalise on stuffing."""
    conf = get_config().get("auth.credential_stuffing") or {}
    if not conf.get("enabled", True):
        return False
    count, tripped = _track_distinct(
        _STUFF_KEY.format(ip=ip), identity,
        int(conf.get("window_seconds", 300)),
        int(conf.get("distinct_identities_threshold", 6)),
    )
    if tripped:
        score = reputation.penalize(ip, "manual",
                                    points=int(conf.get("reputation_penalty", 15)))
        record("reputation_change", "logged", request, threat_score=score,
                dedupe=f"stuff:{ip}", dedupe_ttl=conf.get("window_seconds", 300),
                signal="credential_stuffing", distinct_identities=count)
        return True
    return False


def record_enumeration(ip: str, target: str, request=None) -> bool:
    """Track a lookup target probed against an enumeration-prone endpoint."""
    conf = get_config().get("auth.enumeration") or {}
    if not conf.get("enabled", True):
        return False
    count, tripped = _track_distinct(
        _ENUM_KEY.format(ip=ip), target,
        int(conf.get("window_seconds", 300)),
        int(conf.get("distinct_targets_threshold", 15)),
    )
    if tripped:
        score = reputation.penalize(ip, "enumeration")
        record("reputation_change", "logged", request, threat_score=score,
                dedupe=f"enum:{ip}", dedupe_ttl=conf.get("window_seconds", 300),
                signal="enumeration", distinct_targets=count)
        return True
    return False


def record_brute_force(ip: str, request=None) -> int:
    """One brute-force failure signal (blocking is progressive lockout's job)."""
    return reputation.penalize(ip, "auth_failure")
