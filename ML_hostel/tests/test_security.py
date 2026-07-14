"""Context-token verification tests (no LLM / network needed).

Run: ``cd ML_hostel && ML_SHARED_SECRET=test python -m pytest``
"""
import os
import time

import jwt
import pytest

os.environ.setdefault("ML_SHARED_SECRET", "test-secret")

from app.security import Context, InvalidContext, decode_context  # noqa: E402

SECRET = os.environ["ML_SHARED_SECRET"]


def _mint(**overrides):
    now = int(time.time())
    claims = {
        "tid": "t1", "tname": "Sunrise", "uid": "u1", "role": "WARDEN",
        "perms": ["ai.chat", "rooms.view"], "conv": "c1", "scope": "ai.chat",
        "iat": now, "exp": now + 900,
    }
    claims.update(overrides)
    return jwt.encode(claims, SECRET, algorithm="HS256")


def test_decode_valid():
    ctx = decode_context(_mint())
    assert isinstance(ctx, Context)
    assert ctx.tenant_id == "t1" and ctx.conversation_id == "c1"
    assert "rooms.view" in ctx.perms and ctx.hostel_label == "Sunrise"


def test_tampered_rejected():
    with pytest.raises(InvalidContext):
        decode_context(_mint() + "x")


def test_expired_rejected():
    with pytest.raises(InvalidContext):
        decode_context(_mint(exp=int(time.time()) - 10))


def test_wrong_secret_rejected():
    bad = jwt.encode({"tid": "t1", "exp": int(time.time()) + 60}, "other", algorithm="HS256")
    with pytest.raises(InvalidContext):
        decode_context(bad)
