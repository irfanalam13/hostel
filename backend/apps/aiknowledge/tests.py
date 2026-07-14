"""Tests for the RAG knowledge base (Phase 2).

Retrieval correctness is tested deterministically with hand-crafted vectors (no
LLM/service needed): cosine ranking, tenant isolation, visibility filtering, and
the READY-only rule. Plus KB CRUD RBAC + that a write queues ingestion.
"""
from unittest import mock

import pytest

from apps.assistant.tools import run_tool

from .models import DocumentChunk, KnowledgeDocument

pytestmark = pytest.mark.django_db


def _doc(hostel, title, *, visibility="STAFF", status="READY"):
    return KnowledgeDocument.objects.create(
        hostel=hostel, title=title, source_type="TEXT", content="x",
        visibility=visibility, status=status,
    )


def _chunk(hostel, doc, content, emb, ordinal=0):
    return DocumentChunk.objects.create(
        hostel=hostel, document=doc, ordinal=ordinal, content=content, embedding=emb
    )


def _search(hostel, embedding, perms, role, query="q"):
    return run_tool(
        "search_knowledge", hostel, {"query": query, "embedding": embedding}, perms, role
    )


# --------------------------------------------------------------------------- #
# Retrieval correctness
# --------------------------------------------------------------------------- #
def test_ranks_by_cosine(hostel):
    d1 = _doc(hostel, "Rules")
    _chunk(hostel, d1, "No smoking after 10pm", [1.0, 0.0, 0.0])
    d2 = _doc(hostel, "Fees")
    _chunk(hostel, d2, "Fees are due monthly", [0.0, 1.0, 0.0])

    res = _search(hostel, [0.9, 0.1, 0.0], ["ai.chat"], "WARDEN")
    assert res["results"][0]["title"] == "Rules"
    assert res["results"][0]["score"] > res["results"][1]["score"]


def test_tenant_isolation(hostel, other_hostel):
    d = _doc(other_hostel, "Other tenant doc")
    _chunk(other_hostel, d, "secret", [1.0, 0.0, 0.0])
    res = _search(hostel, [1.0, 0.0, 0.0], ["ai.chat"], "WARDEN")
    assert res["results"] == []


def test_admin_docs_hidden_from_staff(hostel):
    d = _doc(hostel, "Confidential", visibility="ADMIN")
    _chunk(hostel, d, "admin only", [1.0, 0.0, 0.0])
    # staff (no ai.manage, not OWNER/ADMIN) cannot retrieve ADMIN-visibility docs
    staff = _search(hostel, [1.0, 0.0, 0.0], ["ai.chat"], "WARDEN")
    assert staff["results"] == []
    # an owner (ai.manage) can
    owner = _search(hostel, [1.0, 0.0, 0.0], ["ai.chat", "ai.manage"], "OWNER")
    assert len(owner["results"]) == 1


def test_only_ready_documents_retrieved(hostel):
    d = _doc(hostel, "Still ingesting", status="PENDING")
    _chunk(hostel, d, "x", [1.0, 0.0, 0.0])
    res = _search(hostel, [1.0, 0.0, 0.0], ["ai.chat"], "WARDEN")
    assert res["results"] == []


def test_no_embedding_returns_empty(hostel):
    _doc(hostel, "Rules")
    res = run_tool("search_knowledge", hostel, {"query": "q"}, ["ai.chat"], "WARDEN")
    assert res["results"] == []


# --------------------------------------------------------------------------- #
# KB CRUD RBAC + ingestion trigger
# --------------------------------------------------------------------------- #
URL = "/api/ai/knowledge/documents/"


def test_create_requires_ai_manage(auth_client, hostel, warden):
    """WARDEN holds ai.chat/ai.view but not ai.manage -> cannot add KB docs."""
    client = auth_client(warden, hostel)
    with mock.patch("apps.aiknowledge.views.ingest_document.delay") as delay:
        r = client.post(
            URL, {"title": "T", "source_type": "TEXT", "content": "hello"},
            format="json", HTTP_X_HOSTEL_CODE=hostel.code,
        )
    assert r.status_code == 403
    delay.assert_not_called()


def test_owner_create_queues_ingestion(auth_client, hostel, owner):
    client = auth_client(owner, hostel)
    with mock.patch("apps.aiknowledge.views.ingest_document.delay") as delay:
        r = client.post(
            URL, {"title": "Hostel Rules", "source_type": "TEXT", "content": "No smoking."},
            format="json", HTTP_X_HOSTEL_CODE=hostel.code,
        )
    assert r.status_code == 201, r.content
    doc = KnowledgeDocument.objects.get(hostel=hostel, title="Hostel Rules")
    assert doc.status == "PENDING"
    delay.assert_called_once_with(str(doc.id))


def test_list_scoped_to_tenant(auth_client, hostel, other_hostel, owner):
    _doc(hostel, "Mine")
    _doc(other_hostel, "Theirs")
    client = auth_client(owner, hostel)
    r = client.get(URL, HTTP_X_HOSTEL_CODE=hostel.code)
    assert r.status_code == 200, r.content
    data = r.json()["data"]
    rows = data["results"] if isinstance(data, dict) and "results" in data else data
    titles = [d["title"] for d in rows]
    assert "Mine" in titles and "Theirs" not in titles
