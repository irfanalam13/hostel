"""Backup validation — every backup must be provably restorable.

Checks performed:
  * file readability (gzip-decodes + JSON-parses)
  * file integrity (sha256 matches the stored checksum)
  * schema-version compatibility
  * required canonical tables present (residents, billing, payments,
    attendance, rooms/beds)
  * size sanity (not empty / not absurdly large)

:func:`validate_backup` returns a structured report and never raises for a
"bad backup" — callers decide whether to reject. It only raises on programmer
error (e.g. nothing to validate).
"""

from django.conf import settings
from django.utils.timezone import now

from .dump import REQUIRED_SECTIONS, SUPPORTED_SCHEMA_VERSIONS
from .storage import decode_backup_bytes, is_gzip, read_raw_bytes, sha256_hex

# Sanity bounds for the stored (possibly compressed) artifact.
MIN_BACKUP_BYTES = getattr(settings, "BACKUP_MIN_BYTES", 20)
MAX_BACKUP_BYTES = getattr(settings, "BACKUP_MAX_BYTES", 500 * 1024 * 1024)  # 500 MB


def _report():
    return {"ok": False, "checks": {}, "errors": [], "schema_version": None, "sections": {}}


def validate_backup(snapshot=None, *, raw_bytes=None, expected_checksum=None, persist=True):
    """Validate a backup from a snapshot row or raw bytes.

    Returns a report dict: ``{ok, checks{}, errors[], schema_version, sections{}}``.
    When ``snapshot`` is given and ``persist`` is True, the result is written
    back to ``is_valid`` / ``validated_at``.
    """
    report = _report()

    if snapshot is None and raw_bytes is None:
        raise ValueError("validate_backup requires a snapshot or raw_bytes")

    # --- read raw bytes ---
    if raw_bytes is None:
        try:
            raw_bytes = read_raw_bytes(snapshot)
        except Exception as exc:  # noqa: BLE001
            report["errors"].append(f"unreadable file: {exc}")
            report["checks"]["readable"] = False
            return _finish(report, snapshot, persist)

    if expected_checksum is None and snapshot is not None:
        expected_checksum = snapshot.checksum or None

    # --- size sanity ---
    size = len(raw_bytes)
    size_ok = MIN_BACKUP_BYTES <= size <= MAX_BACKUP_BYTES
    report["checks"]["size_sanity"] = size_ok
    report["checks"]["size_bytes"] = size
    if not size_ok:
        report["errors"].append(
            f"size {size}B outside sane bounds [{MIN_BACKUP_BYTES}, {MAX_BACKUP_BYTES}]"
        )

    # --- file integrity (checksum) ---
    actual_checksum = sha256_hex(raw_bytes)
    report["checks"]["checksum"] = actual_checksum
    if expected_checksum:
        match = actual_checksum == expected_checksum
        report["checks"]["checksum_match"] = match
        if not match:
            report["errors"].append("checksum mismatch (file corrupted or altered)")
    report["checks"]["compressed"] = is_gzip(raw_bytes)

    # --- readability (decompress + parse) ---
    try:
        data = decode_backup_bytes(raw_bytes)
        report["checks"]["readable"] = True
    except Exception as exc:  # noqa: BLE001
        report["checks"]["readable"] = False
        report["errors"].append(f"not parseable: {exc}")
        return _finish(report, snapshot, persist)

    if not isinstance(data, dict):
        report["checks"]["structure"] = False
        report["errors"].append("backup root is not a JSON object")
        return _finish(report, snapshot, persist)
    report["checks"]["structure"] = True

    # --- schema version compatibility ---
    schema_version = data.get("schema_version")
    report["schema_version"] = schema_version
    schema_ok = schema_version in SUPPORTED_SCHEMA_VERSIONS
    report["checks"]["schema_compatible"] = schema_ok
    if not schema_ok:
        report["errors"].append(
            f"schema_version {schema_version!r} not in supported {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )

    # --- required tables present ---
    missing = [s for s in REQUIRED_SECTIONS if s not in data]
    report["checks"]["required_tables_present"] = not missing
    if missing:
        report["errors"].append(f"missing required sections: {missing}")
    report["sections"] = {
        s: (len(data[s]) if isinstance(data.get(s), list) else None) for s in REQUIRED_SECTIONS
    }

    report["ok"] = not report["errors"]
    return _finish(report, snapshot, persist)


def _finish(report, snapshot, persist):
    report["ok"] = not report["errors"]
    if snapshot is not None and persist:
        snapshot.is_valid = report["ok"]
        snapshot.validated_at = now()
        snapshot.save(update_fields=["is_valid", "validated_at"])
    return report
