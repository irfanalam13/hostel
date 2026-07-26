"""Tamper-evidence primitives for the audit trail.

Every :class:`~apps.auditlog.models.AuditEvent` row is linked into an
append-only hash chain: the row's ``content_hash`` is the SHA-256 of its own
canonical content concatenated with the ``content_hash`` of the row before it
(``prev_hash``). Changing, reordering or deleting any historical row breaks the
chain from that point forward, which the verifier detects.

We hash SHA-256 (never MD5/SHA-1) to match the project's existing
abuse-fingerprint hashing decision. The canonical serialization is a compact,
sorted-key JSON blob so the digest is stable regardless of dict ordering.
"""
from __future__ import annotations

import hashlib
import json

# prev_hash of the very first row (or the first row after a retention
# checkpoint). 64 zeros = "no predecessor".
GENESIS_HASH = "0" * 64

# Fields that make up a row's tamper-evident content, in a fixed order. Adding a
# field here changes every hash, so it must only ever grow at the end and be
# paired with a chain rebuild migration.
HASHED_FIELDS = (
    "sequence",
    "action",
    "actor_id",
    "hostel_id",
    "branch_id",
    "entity_type",
    "entity_id",
    "message",
    "reason",
    "meta",
    "changes",
    "ip_address",
    "user_agent",
    "request_id",
    "result",
    "status_code",
    "duration_ms",
    "created_at",
)


def _normalize(value):
    """Make a value stable and JSON-serializable for hashing."""
    if value is None:
        return None
    # datetimes -> ISO 8601 (UTC-aware or naive, both str() deterministically)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    # UUIDs, Decimals, etc.
    if isinstance(value, (dict, list, str, int, float, bool)):
        return value
    return str(value)


def canonical_content(fields: dict) -> str:
    """Deterministic JSON string of the hashed portion of a row."""
    payload = {name: _normalize(fields.get(name)) for name in HASHED_FIELDS}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(fields: dict, prev_hash: str) -> str:
    """SHA-256 of ``canonical(fields) + prev_hash`` -> hex digest."""
    material = f"{canonical_content(fields)}|{prev_hash or GENESIS_HASH}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def fields_from_instance(instance) -> dict:
    """Extract the hashed fields off an AuditEvent instance.

    Single source of truth shared by the writer (``create_chained``) and the
    verifier so both hash *exactly* the same values — including model-applied
    defaults ("" for blank CharFields, {} for JSON, etc.). Hashing raw kwargs
    instead would diverge from the persisted row.
    """
    return {name: getattr(instance, name) for name in HASHED_FIELDS}


def instance_hash(instance, prev_hash: str) -> str:
    """Content hash of an AuditEvent instance chained to ``prev_hash``."""
    return compute_hash(fields_from_instance(instance), prev_hash)
