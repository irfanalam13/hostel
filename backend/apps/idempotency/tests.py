"""Unit tests for IdempotencyMiddleware (RequestFactory — no auth/tenant setup).

Verifies the offline-sync guarantees: a replayed request returns the stored
response without re-running the view, payload integrity is enforced, and reusing
a key with a different body is rejected.
"""
import hashlib
import json

import pytest
from django.http import JsonResponse
from django.test import RequestFactory

from apps.idempotency.middleware import IdempotencyMiddleware
from apps.idempotency.models import IdempotencyRecord


@pytest.mark.django_db
class TestIdempotencyMiddleware:
    def _mw(self, calls):
        def get_response(request):
            calls.append(1)
            return JsonResponse({"id": "abc", "created": True}, status=201)

        return IdempotencyMiddleware(get_response)

    def _post(self, body):
        rf = RequestFactory()
        payload = json.dumps(body)
        checksum = hashlib.sha256(payload.encode()).hexdigest()
        return rf.post(
            "/api/students/students/",
            data=payload,
            content_type="application/json",
            headers={"idempotency-key": "key-123", "x-payload-checksum": checksum},
        )

    def test_first_request_runs_view_and_stores(self):
        calls = []
        mw = self._mw(calls)
        resp = mw(self._post({"full_name": "ABC"}))
        assert resp.status_code == 201
        assert len(calls) == 1
        rec = IdempotencyRecord.objects.get(key="key-123")
        assert rec.status_code == 201

    def test_replay_returns_stored_without_rerunning_view(self):
        calls = []
        mw = self._mw(calls)
        mw(self._post({"full_name": "ABC"}))
        resp2 = mw(self._post({"full_name": "ABC"}))
        assert resp2.status_code == 201
        assert resp2["Idempotent-Replay"] == "true"
        assert len(calls) == 1  # view NOT called again
        assert IdempotencyRecord.objects.filter(key="key-123").count() == 1

    def test_checksum_mismatch_rejected(self):
        calls = []
        mw = self._mw(calls)
        rf = RequestFactory()
        req = rf.post(
            "/api/x/",
            data=json.dumps({"a": 1}),
            content_type="application/json",
            headers={"idempotency-key": "k2", "x-payload-checksum": "deadbeef"},
        )
        resp = mw(req)
        assert resp.status_code == 400
        assert len(calls) == 0

    def test_same_key_different_body_conflicts(self):
        calls = []
        mw = self._mw(calls)
        mw(self._post({"full_name": "ABC"}))
        resp = mw(self._post({"full_name": "DIFFERENT"}))
        assert resp.status_code == 409
        assert len(calls) == 1

    def test_no_key_passes_through(self):
        calls = []
        mw = self._mw(calls)
        rf = RequestFactory()
        resp = mw(rf.post("/api/x/", data="{}", content_type="application/json"))
        assert resp.status_code == 201
        assert len(calls) == 1
        assert IdempotencyRecord.objects.count() == 0
