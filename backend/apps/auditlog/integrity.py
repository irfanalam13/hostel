"""Audit hash-chain verification.

Walks surviving events in sequence order and recomputes each row's hash,
confirming (a) every ``content_hash`` matches the row's content, (b) each row's
``prev_hash`` equals the previous row's ``content_hash``, and (c) there are no
sequence gaps. The walk starts from the retention checkpoint so a pruned tail
doesn't produce false positives.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .hashing import instance_hash
from .models import AuditChainState, AuditEvent


@dataclass
class VerifyResult:
    ok: bool = True
    checked: int = 0
    first_bad_sequence: int | None = None
    reason: str = ""
    errors: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "checked": self.checked,
            "first_bad_sequence": self.first_bad_sequence,
            "reason": self.reason,
            "errors": self.errors[:50],
        }


def verify_chain(limit: int | None = None) -> VerifyResult:
    """Verify the whole surviving chain (or the newest ``limit`` rows)."""
    state = AuditChainState.load()
    result = VerifyResult()

    qs = AuditEvent.objects.filter(sequence__isnull=False).order_by("sequence")
    if limit:
        # Verify only the most recent `limit` rows: we still need the row
        # before the window to seed prev_hash, so grab limit+1.
        recent = list(qs.reverse()[: limit + 1])
        recent.reverse()
        events = recent
        expected_prev = events[0].prev_hash if events else state.checkpoint_hash
        events = events[1:] if len(events) > limit else events
    else:
        events = qs.iterator()
        expected_prev = state.checkpoint_hash

    prev_hash = expected_prev
    expected_seq = None

    for event in events:
        result.checked += 1

        if expected_seq is not None and event.sequence != expected_seq:
            result.ok = False
            result.first_bad_sequence = result.first_bad_sequence or event.sequence
            result.errors.append(
                f"sequence gap: expected {expected_seq}, found {event.sequence}"
            )

        if event.prev_hash != prev_hash:
            result.ok = False
            result.first_bad_sequence = result.first_bad_sequence or event.sequence
            result.errors.append(
                f"seq {event.sequence}: prev_hash mismatch (chain broken/reordered)"
            )

        recomputed = instance_hash(event, event.prev_hash)
        if recomputed != event.content_hash:
            result.ok = False
            result.first_bad_sequence = result.first_bad_sequence or event.sequence
            result.errors.append(
                f"seq {event.sequence}: content_hash mismatch (row tampered)"
            )

        prev_hash = event.content_hash
        expected_seq = event.sequence + 1

    # The tip must match the recorded chain head (catches deletion of the
    # newest rows, which walking-forward alone can't see).
    if not limit and prev_hash != (state.last_hash or state.checkpoint_hash):
        if result.checked or state.sequence:
            result.ok = False
            result.errors.append(
                "chain tip does not match recorded head (newest rows deleted?)"
            )

    if not result.ok and not result.reason:
        result.reason = "integrity check failed"
    return result
