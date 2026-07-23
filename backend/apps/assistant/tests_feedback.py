"""Feedback endpoint + eval-export drift loop tests (Phase 6 AI/MLOps)."""
import json

import pytest
from django.core.management import call_command
from django.urls import reverse

from .models import AiUsage, Conversation, Message

pytestmark = pytest.mark.django_db


def _hdr(hostel):
    return {"HTTP_X_HOSTEL_CODE": hostel.code}


def test_feedback_records_on_latest_usage(auth_client, hostel, warden):
    client = auth_client(warden, hostel)
    conv = Conversation.objects.create(hostel=hostel, user=warden, title="t")
    usage = AiUsage.objects.create(hostel=hostel, conversation=conv, model="gemini-flash-latest")

    resp = client.post(
        reverse("ai-conv-feedback", args=[conv.id]),
        {"rating": "down", "note": "wrong number"}, format="json", **_hdr(hostel),
    )
    assert resp.status_code == 200, resp.content
    usage.refresh_from_db()
    assert usage.meta["feedback"]["rating"] == "down"
    assert usage.meta["feedback"]["note"] == "wrong number"


def test_feedback_rejects_bad_rating(auth_client, hostel, warden):
    client = auth_client(warden, hostel)
    conv = Conversation.objects.create(hostel=hostel, user=warden, title="t")
    AiUsage.objects.create(hostel=hostel, conversation=conv)
    resp = client.post(
        reverse("ai-conv-feedback", args=[conv.id]), {"rating": "meh"}, format="json", **_hdr(hostel)
    )
    assert resp.status_code == 400


def test_eval_export_collects_negative_cases(hostel, warden, tmp_path):
    conv = Conversation.objects.create(hostel=hostel, user=warden, title="t")
    Message.objects.create(conversation=conv, role=Message.Role.USER, content="How many beds free?")
    Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="42 (wrong)")
    AiUsage.objects.create(
        hostel=hostel, conversation=conv, model="gemini-flash-latest",
        meta={"prompt_version": "2026.07.1", "feedback": {"rating": "down", "note": "hallucinated"}},
    )
    # A thumbs-up answer must NOT be exported.
    conv2 = Conversation.objects.create(hostel=hostel, user=warden, title="good")
    AiUsage.objects.create(hostel=hostel, conversation=conv2, meta={"feedback": {"rating": "up"}})

    out = tmp_path / "cands.json"
    call_command("ai_eval_export", "--days", "30", "--out", str(out))

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["count"] == 1
    c = data["candidates"][0]
    assert c["reason"] == "thumbs_down"
    assert c["question"] == "How many beds free?"
    assert c["prompt_version"] == "2026.07.1"
