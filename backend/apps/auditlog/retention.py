"""Retention + archiving for audit events.

Deleting audit rows would break the hash chain, so retention instead
*archives-then-prunes*: the oldest contiguous block of events beyond the
retention window is exported to an append-only JSONL file, then removed, and
the chain checkpoint is advanced to the last archived row. Verification of the
surviving tail continues from that checkpoint, so tamper-evidence is preserved
across pruning.

Configure with ``AUDIT_RETENTION_DAYS`` (default 365) and ``AUDIT_ARCHIVE_DIR``
(default ``<BASE_DIR>/audit-archive``). Set retention to 0 to keep everything.
"""
from __future__ import annotations

import json
import logging
import os

from django.conf import settings
from django.utils import timezone

from .models import AuditChainState, AuditEvent

logger = logging.getLogger("apps.auditlog")

_EXPORT_FIELDS = (
    "id", "sequence", "prev_hash", "content_hash", "action", "actor_id",
    "hostel_id", "branch_id", "entity_type", "entity_id", "message", "reason",
    "meta", "changes", "ip_address", "user_agent", "request_id", "result",
    "status_code", "duration_ms", "created_at",
)


def _archive_dir() -> str:
    return str(getattr(settings, "AUDIT_ARCHIVE_DIR", None)
               or os.path.join(str(settings.BASE_DIR), "audit-archive"))


def _serialize(event: AuditEvent) -> dict:
    row = {}
    for name in _EXPORT_FIELDS:
        value = getattr(event, name)
        row[name] = value.isoformat() if hasattr(value, "isoformat") else value
    return row


def prune_expired(retention_days: int | None = None, batch: int = 5000) -> dict:
    """Archive + delete events older than the retention window.

    Returns a summary dict. Only prunes a *contiguous prefix* of the chain
    (oldest rows) so the surviving tail stays a valid, verifiable chain rooted
    at the new checkpoint.
    """
    if retention_days is None:
        retention_days = int(getattr(settings, "AUDIT_RETENTION_DAYS", 365))
    if retention_days <= 0:
        return {"archived": 0, "deleted": 0, "skipped": "retention disabled"}

    cutoff = timezone.now() - timezone.timedelta(days=retention_days)
    state = AuditChainState.load()

    expired = (
        AuditEvent.objects.filter(
            sequence__isnull=False,
            sequence__gt=state.checkpoint_sequence,
            created_at__lt=cutoff,
        )
        .order_by("sequence")[:batch]
    )
    expired = list(expired)
    if not expired:
        return {"archived": 0, "deleted": 0}

    # Only prune a contiguous run starting right after the checkpoint; stop at
    # the first gap so we never orphan the surviving tail's prev_hash link.
    contiguous = []
    expected = state.checkpoint_sequence + 1
    for event in expired:
        if event.sequence != expected:
            break
        contiguous.append(event)
        expected += 1
    if not contiguous:
        return {"archived": 0, "deleted": 0}

    os.makedirs(_archive_dir(), exist_ok=True)
    stamp = timezone.now().strftime("%Y%m%d")
    path = os.path.join(_archive_dir(), f"audit-{stamp}.jsonl")
    with open(path, "a", encoding="utf-8") as fh:
        for event in contiguous:
            fh.write(json.dumps(_serialize(event), default=str) + "\n")

    last = contiguous[-1]
    ids = [e.id for e in contiguous]
    AuditEvent.objects.filter(id__in=ids)._archive_delete()

    state.checkpoint_sequence = last.sequence
    state.checkpoint_hash = last.content_hash
    state.save(update_fields=["checkpoint_sequence", "checkpoint_hash", "updated_at"])

    logger.info(
        "audit retention: archived+pruned %d events (through seq %d) to %s",
        len(contiguous), last.sequence, path,
    )
    return {
        "archived": len(contiguous),
        "deleted": len(contiguous),
        "checkpoint_sequence": last.sequence,
        "archive_file": path,
    }
