"""Short-lived context tokens bridging Django and the ML_hostel service.

The gateway mints an HMAC-signed JWT that captures *who* is asking and *what
they may see* (tenant + user + the caller's already-resolved permission set).
The ML service verifies it and echoes it back on every tool callback, so the
assistant can never reach data the caller couldn't reach through the normal API.

PyJWT ships transitively via ``djangorestframework-simplejwt``; both this module
and the standalone FastAPI service decode with the same HS256 secret, so no
Django import is required on the service side.
"""
import time

import jwt
from django.conf import settings


def _secret() -> str:
    # Dedicated secret in prod; fall back to SECRET_KEY so dev boots unconfigured.
    return settings.ML_SHARED_SECRET or settings.SECRET_KEY


def mint_context_token(*, hostel, user, perms, conversation_id, scope="ai.chat", ttl=None) -> str:
    ttl = int(ttl or settings.ML_TOKEN_TTL)
    now = int(time.time())
    payload = {
        "tid": str(hostel.id),
        "tslug": getattr(hostel, "slug", ""),
        "tname": getattr(hostel, "name", "") or getattr(hostel, "slug", ""),
        "uid": str(user.id),
        "role": getattr(user, "role", "") or "",
        "perms": sorted(perms),
        "conv": str(conversation_id),
        "scope": scope,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def mint_system_token(*, hostel, scope="ai.ingest", ttl=None) -> str:
    """A tenant-scoped token for background/system callers (no human actor).

    Used by the ingestion pipeline to call the ML service for embeddings. Carries
    no permissions — the service only needs a valid, tenant-bound, secret-signed
    token to trust the caller for stateless embedding work.
    """
    ttl = int(ttl or settings.ML_TOKEN_TTL)
    now = int(time.time())
    payload = {
        "tid": str(hostel.id),
        "tslug": getattr(hostel, "slug", ""),
        "tname": getattr(hostel, "name", "") or getattr(hostel, "slug", ""),
        "uid": "system",
        "role": "SYSTEM",
        "perms": [],
        "conv": "",
        "scope": scope,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def verify_context_token(token: str) -> dict:
    """Decode + validate (raises ``jwt.PyJWTError`` on tamper/expiry)."""
    return jwt.decode(token, _secret(), algorithms=["HS256"])
