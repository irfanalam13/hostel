"""Tests for the AI assistant gateway.

Covers the two auth paths (browser session cookie for chat; Bearer context
token for the service callbacks), RBAC on both, tenant isolation of tools, and
the completion write-back. The ML service itself is not exercised here — the
gateway is provably correct on its own.
"""
import jwt
import pytest
from django.urls import reverse

from apps.students.models import Student

from .models import AiUsage, Conversation, Message
from .tokens import mint_context_token, verify_context_token

pytestmark = pytest.mark.django_db


def _hdr(hostel):
    return {"HTTP_X_HOSTEL_CODE": hostel.code}


def body(resp):
    """Unwrap the standard ``{success, data, ...}`` response envelope."""
    j = resp.json()
    return j.get("data", j) if isinstance(j, dict) else j


def _bearer(client, token):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


def jwt_for(hostel, *, perms, role):
    """Mint a context token without a real user object (service-path tests)."""
    from types import SimpleNamespace

    # any uuid for id; the tool path only reads tid/perms/role from the token
    user = SimpleNamespace(id=hostel.id, role=role)
    return mint_context_token(hostel=hostel, user=user, perms=perms, conversation_id=hostel.id)


# --------------------------------------------------------------------------- #
# Context token
# --------------------------------------------------------------------------- #
def test_token_roundtrip(hostel, warden):
    conv = Conversation.objects.create(hostel=hostel, user=warden, title="t")
    token = mint_context_token(
        hostel=hostel, user=warden, perms=["ai.chat", "rooms.view"], conversation_id=conv.id
    )
    claims = verify_context_token(token)
    assert claims["tid"] == str(hostel.id)
    assert claims["uid"] == str(warden.id)
    assert claims["conv"] == str(conv.id)
    assert "rooms.view" in claims["perms"]


def test_tampered_token_rejected(hostel, warden):
    token = mint_context_token(
        hostel=hostel, user=warden, perms=[], conversation_id=warden.id
    )
    with pytest.raises(jwt.PyJWTError):
        verify_context_token(token + "x")


# The claims the standalone ML_hostel service reads in
# ``ML_hostel/app/security.py::decode_context``. It uses ``claims.get(...)`` with
# empty defaults, so a silent rename here would NOT raise on the service side —
# it would quietly drop tenant/permission context and break RBAC/tenant
# isolation. This contract test fails fast on any such drift. Keep it in lockstep
# with the ML service's ``Context`` dataclass. (Phase 0, §2 AI overlay.)
ML_CONSUMED_CLAIMS = {"tid", "tname", "uid", "role", "perms", "conv"}
# The full payload Django mints (superset of what the ML service consumes today).
CONTEXT_TOKEN_CLAIMS = ML_CONSUMED_CLAIMS | {"tslug", "scope", "iat", "exp"}


def test_context_token_claim_contract(hostel, warden):
    """Pin the context-token payload shape against the ML service contract."""
    conv = Conversation.objects.create(hostel=hostel, user=warden, title="t")
    claims = verify_context_token(
        mint_context_token(
            hostel=hostel, user=warden, perms=["ai.chat"], conversation_id=conv.id
        )
    )
    # Every claim the ML service depends on must be present and non-null.
    missing = ML_CONSUMED_CLAIMS - claims.keys()
    assert not missing, f"context token dropped ML-consumed claims: {missing}"
    # And the minted set must match the documented contract exactly (catches both
    # silent additions and removals — either side of the contract can drift).
    assert set(claims) == CONTEXT_TOKEN_CLAIMS


def test_system_token_claim_contract(hostel):
    """The system/ingest token must satisfy the same ML-consumed claim set."""
    from .tokens import mint_system_token

    claims = verify_context_token(mint_system_token(hostel=hostel))
    missing = ML_CONSUMED_CLAIMS - claims.keys()
    assert not missing, f"system token dropped ML-consumed claims: {missing}"
    assert claims["role"] == "SYSTEM" and claims["perms"] == []


# --------------------------------------------------------------------------- #
# Browser-facing chat (session cookie + RBAC + plan)
# --------------------------------------------------------------------------- #
def test_chat_start_creates_conversation(auth_client, hostel, warden):
    client = auth_client(warden, hostel)
    resp = client.post(
        reverse("ai-chat"), {"message": "How many beds are free?"}, format="json", **_hdr(hostel)
    )
    assert resp.status_code == 201, resp.content
    data = body(resp)
    assert data["stream_url"].endswith("/v1/chat/stream")
    assert data["token"]
    conv = Conversation.objects.get(pk=data["conversation_id"])
    assert conv.user == warden and conv.hostel == hostel
    assert conv.messages.filter(role="user").count() == 1


def test_chat_denied_without_permission(auth_client, hostel, resident_user):
    """A RESIDENT has no ai.chat grant -> 403 even though they're a member."""
    client = auth_client(resident_user, hostel)
    resp = client.post(reverse("ai-chat"), {"message": "hi"}, format="json", **_hdr(hostel))
    assert resp.status_code == 403


def test_chat_requires_message(auth_client, hostel, warden):
    client = auth_client(warden, hostel)
    resp = client.post(reverse("ai-chat"), {"message": "  "}, format="json", **_hdr(hostel))
    assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# Service-facing tools (Bearer context token + RBAC + tenancy)
# --------------------------------------------------------------------------- #
def test_tool_run_allowed(api, hostel, warden):
    token = mint_context_token(
        hostel=hostel, user=warden, perms=["rooms.view"], conversation_id=warden.id
    )
    _bearer(api, token)
    resp = api.post(reverse("ai-tool-run", args=["occupancy_summary"]), {}, format="json")
    assert resp.status_code == 200, resp.content
    assert "occupancy_percent" in body(resp)["result"]


def test_tool_run_forbidden_without_guard(api, hostel):
    """A non-staff caller cannot run the staff-only student search."""
    token = jwt_for(hostel, perms=[], role="RESIDENT")
    _bearer(api, token)
    resp = api.post(reverse("ai-tool-run", args=["find_students"]), {"query": "x"}, format="json")
    assert resp.status_code == 403


def test_tool_unknown(api, hostel, warden):
    token = mint_context_token(
        hostel=hostel, user=warden, perms=["rooms.view"], conversation_id=warden.id
    )
    _bearer(api, token)
    resp = api.post(reverse("ai-tool-run", args=["does_not_exist"]), {}, format="json")
    assert resp.status_code == 404


def test_tool_no_token_rejected(api):
    resp = api.post(reverse("ai-tool-run", args=["occupancy_summary"]), {}, format="json")
    assert resp.status_code in (401, 403)


def test_tool_tenant_isolation(api, hostel, other_hostel, warden):
    """find_students only ever sees the token's own workspace."""
    import datetime as dt

    Student.objects.create(
        hostel=hostel, full_name="Mine", phone="9800000001", status="ACTIVE", join_date=dt.date.today()
    )
    Student.objects.create(
        hostel=other_hostel, full_name="Theirs", phone="9800000002", status="ACTIVE", join_date=dt.date.today()
    )
    token = jwt_for(hostel, perms=["ai.chat"], role="WARDEN")
    _bearer(api, token)
    resp = api.post(reverse("ai-tool-run", args=["find_students"]), {"query": ""}, format="json")
    assert resp.status_code == 200, resp.content
    names = [r["full_name"] for r in body(resp)["result"]["results"]]
    assert "Mine" in names and "Theirs" not in names


# --------------------------------------------------------------------------- #
# Completion write-back
# --------------------------------------------------------------------------- #
def test_complete_persists_message_and_usage(api, hostel, warden):
    conv = Conversation.objects.create(hostel=hostel, user=warden, title="t")
    token = mint_context_token(
        hostel=hostel, user=warden, perms=["ai.chat"], conversation_id=conv.id
    )
    _bearer(api, token)
    resp = api.post(
        reverse("ai-conv-complete", args=[conv.id]),
        {
            "content": "You have 4 free beds.",
            "provider": "ollama",
            "model": "llama3.2",
            "tokens_prompt": 120,
            "tokens_completion": 30,
            "latency_ms": 850,
            "tool_calls": [{"name": "occupancy_summary"}],
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert Message.objects.filter(conversation=conv, role="assistant").count() == 1
    usage = AiUsage.objects.get(conversation=conv)
    assert usage.tokens_total == 150 and usage.model == "llama3.2" and usage.success is True
    conv.refresh_from_db()
    assert conv.model == "llama3.2"


def test_complete_persists_sources(api, hostel, warden):
    """RAG citations from the service are stored on the usage record."""
    conv = Conversation.objects.create(hostel=hostel, user=warden, title="t")
    token = mint_context_token(
        hostel=hostel, user=warden, perms=["ai.chat"], conversation_id=conv.id
    )
    _bearer(api, token)
    resp = api.post(
        reverse("ai-conv-complete", args=[conv.id]),
        {
            "content": "According to the Hostel Rules, quiet hours are 10 PM–6 AM.",
            "provider": "ollama",
            "model": "llama3.2",
            "tool_calls": [{"name": "search_knowledge"}],
            "sources": [{"title": "Hostel Rules 2026", "document_id": "d1"}],
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    usage = AiUsage.objects.get(conversation=conv)
    assert usage.meta["sources"] == [{"title": "Hostel Rules 2026", "document_id": "d1"}]
    assert usage.meta["tool_calls"] == ["search_knowledge"]
