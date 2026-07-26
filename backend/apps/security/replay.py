"""Replay / nonce protection for one-time operations.

A generic "consume once within a TTL" primitive on Redis, for surfaces where
a captured-and-resent request must not succeed twice:

* incoming webhooks (dedupe by provider event id / signature)
* signed API requests (nonce + timestamp)
* any OTP/token whose single-use must hold even across a race

Usage::

    from apps.security.replay import seen_before
    if seen_before("webhook:stripe", event_id, ttl=86400):
        return HttpResponse(status=200)   # already processed — ignore

``seen_before`` is atomic (SET NX): the first caller gets False and claims the
nonce, every later caller within the TTL gets True. When Redis is unavailable
it fails **closed for replay** (returns True = treat as replay) only if
``fail_closed`` is passed — by default it fails open (returns False) so a Redis
outage doesn't reject legitimate first-time requests. JWT replay itself is
already handled structurally (SimpleJWT rotation + blacklist + the ``pwv``
fingerprint); this covers everything that isn't a JWT.
"""
import hashlib
import logging

from . import redis_client

logger = logging.getLogger("apps.security")

_KEY = "sec:replay:{scope}:{nonce}"


def _norm(nonce: str) -> str:
    nonce = (nonce or "").strip()
    # Hash long/opaque nonces (signatures, tokens) to a bounded key.
    return hashlib.sha256(nonce.encode()).hexdigest()[:32] if len(nonce) > 64 else nonce


def seen_before(scope: str, nonce: str, ttl: int = 86400,
                fail_closed: bool = False) -> bool:
    """True if this (scope, nonce) was already consumed within ``ttl``.
    The first caller consumes it and gets False."""
    if not nonce:
        return False
    client = redis_client.get_client()
    if client is None:
        return fail_closed
    try:
        # NX succeeds only for the first caller -> not a replay.
        claimed = client.set(_KEY.format(scope=scope, nonce=_norm(nonce)),
                             1, nx=True, ex=int(ttl))
        return not claimed
    except Exception:
        redis_client.mark_down()
        return fail_closed


def forget(scope: str, nonce: str) -> None:
    """Release a nonce (e.g. after a webhook handler fails and should retry)."""
    client = redis_client.get_client()
    if client is None:
        return
    try:
        client.delete(_KEY.format(scope=scope, nonce=_norm(nonce)))
    except Exception:
        redis_client.mark_down()
