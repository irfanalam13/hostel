"""Idempotency + payload-integrity middleware for offline-sync replays.

When the PWA replays a queued offline write after reconnecting, it sends an
``Idempotency-Key`` header (a UUID generated once for that logical action) and an
``X-Payload-Checksum`` (sha256 of the body). This middleware:

  * verifies integrity — server-computed body hash must match X-Payload-Checksum;
  * detects duplicates — if the key was already processed, it returns the stored
    response instead of running the view again (so a lost ack can't create a
    second record);
  * rejects key reuse — same key + a different payload → 409.

Placed after auth + tenant resolution (so request.user / request.hostel exist)
and before AxesMiddleware.
"""
import hashlib
import json

from django.db import IntegrityError, transaction
from django.http import HttpResponse

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
MAX_STORED_BODY = 100_000  # cap stored response size


def _json(status, payload):
    return HttpResponse(json.dumps(payload), status=status, content_type="application/json")


class IdempotencyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        key = request.headers.get("Idempotency-Key")
        if request.method in SAFE_METHODS or not key:
            return self.get_response(request)

        # request.body is cached by Django, so the view can still read it afterwards.
        try:
            body = request.body
        except Exception:
            body = b""
        request_hash = hashlib.sha256(body).hexdigest()

        # Integrity: client checksum (if sent) must match the server-computed hash.
        client_checksum = request.headers.get("X-Payload-Checksum")
        if client_checksum and client_checksum.lower() != request_hash:
            return _json(400, {"detail": "Payload integrity check failed (checksum mismatch)."})

        # Local import keeps the app loadable before migrations run.
        from .models import IdempotencyRecord

        existing = IdempotencyRecord.objects.filter(key=key).first()
        if existing:
            if existing.request_hash and existing.request_hash != request_hash:
                return _json(409, {"detail": "Idempotency-Key already used with a different payload."})
            if existing.status_code:
                return self._replay(existing)
            return _json(409, {"detail": "A request with this Idempotency-Key is already in progress."})

        # Reserve the key (in-progress marker). A concurrent replay racing us will
        # hit the unique constraint and fall back to replay/conflict handling.
        try:
            with transaction.atomic():
                record = IdempotencyRecord.objects.create(
                    key=key,
                    hostel_id=getattr(getattr(request, "hostel", None), "id", None),
                    user=request.user
                    if getattr(getattr(request, "user", None), "is_authenticated", False)
                    else None,
                    method=request.method,
                    path=request.path[:300],
                    request_hash=request_hash,
                    status_code=0,
                )
        except IntegrityError:
            existing = IdempotencyRecord.objects.filter(key=key).first()
            if existing and existing.status_code:
                return self._replay(existing)
            return _json(409, {"detail": "A request with this Idempotency-Key is already in progress."})

        response = self.get_response(request)
        self._persist(record, response)
        return response

    def _persist(self, record, response):
        """Cache deterministic outcomes (2xx/4xx) for replay; drop the reservation
        on 5xx/streaming so a genuine retry can still go through."""
        try:
            if getattr(response, "streaming", False) or response.status_code >= 500:
                record.delete()
                return
            content = response.content.decode("utf-8", errors="replace")[:MAX_STORED_BODY]
            record.status_code = response.status_code
            record.response_body = content
            record.save(update_fields=["status_code", "response_body", "updated_at"])
        except Exception:
            # Never let bookkeeping break the actual response.
            try:
                record.delete()
            except Exception:
                pass

    def _replay(self, record):
        resp = HttpResponse(
            record.response_body,
            status=record.status_code,
            content_type="application/json",
        )
        resp["Idempotent-Replay"] = "true"
        return resp
