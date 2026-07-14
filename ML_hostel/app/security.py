"""Context-token verification.

The token is an HS256 JWT minted by Django (apps.assistant.tokens) that carries
the tenant, the user, and the caller's already-resolved permission set. We only
verify + decode it — we never issue one and never widen its claims.
"""
from dataclasses import dataclass

import jwt

from .config import settings


@dataclass
class Context:
    tenant_id: str
    tenant_name: str
    user_id: str
    role: str
    perms: list[str]
    conversation_id: str
    token: str  # the raw token, echoed back on gateway callbacks

    @property
    def hostel_label(self) -> str:
        return self.tenant_name or self.tenant_id


class InvalidContext(Exception):
    pass


def decode_context(token: str) -> Context:
    if not settings.SHARED_SECRET:
        # Fail closed: without the shared secret we cannot trust anything.
        raise InvalidContext("ML service is not configured with ML_SHARED_SECRET")
    try:
        claims = jwt.decode(token, settings.SHARED_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:  # expired / tampered / wrong secret
        raise InvalidContext(str(exc)) from exc
    return Context(
        tenant_id=claims.get("tid", ""),
        tenant_name=claims.get("tname", ""),
        user_id=claims.get("uid", ""),
        role=claims.get("role", ""),
        perms=claims.get("perms", []),
        conversation_id=claims.get("conv", ""),
        token=token,
    )
