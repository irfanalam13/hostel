"""Backup file storage: naming, compression, checksums, read/write helpers.

Backups are JSON documents (see :mod:`apps.backups.dump`), gzip-compressed on
disk and laid out by retention bucket::

    backups/daily/<hostel>_<timestamp>_v<schema>.json.gz
    backups/weekly/...
    backups/monthly/...
    backups/manual/...
    backups/pre_restore/...
"""

import gzip
import hashlib
import json

from django.core.files.base import ContentFile
from django.utils.timezone import now

from .dump import BACKUP_SCHEMA_VERSION, build_hostel_dump
from .models import BackupPeriod, BackupSnapshot

GZIP_MAGIC = b"\x1f\x8b"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def gzip_bytes(data: bytes) -> bytes:
    # mtime=0 → deterministic output (same data ⇒ same checksum).
    return gzip.compress(data, mtime=0)


def gunzip_bytes(data: bytes) -> bytes:
    return gzip.decompress(data)


def is_gzip(data: bytes) -> bool:
    return data[:2] == GZIP_MAGIC


def build_filename(hostel, period: str, schema_version: int, when=None, compressed=True) -> str:
    """Unique name: <hostelcode>_<UTC timestamp>_v<schema>.json[.gz]."""
    when = when or now()
    stamp = when.strftime("%Y%m%dT%H%M%S")
    ext = "json.gz" if compressed else "json"
    code = (hostel.code or f"hostel{hostel.id}").replace("/", "-")
    return f"{code}_{stamp}_v{schema_version}.{ext}"


def read_raw_bytes(snapshot: BackupSnapshot) -> bytes:
    snapshot.file.open("rb")
    try:
        return snapshot.file.read()
    finally:
        snapshot.file.close()


def load_backup_data(snapshot: BackupSnapshot) -> dict:
    """Return the parsed JSON dict from a snapshot, transparently decompressing."""
    raw = read_raw_bytes(snapshot)
    return decode_backup_bytes(raw)


def decode_backup_bytes(raw: bytes) -> dict:
    payload = gunzip_bytes(raw) if is_gzip(raw) else raw
    return json.loads(payload.decode("utf-8"))


def create_snapshot(
    hostel,
    *,
    period: str = BackupPeriod.MANUAL,
    kind: str = "manual",
    note: str = "",
    data: dict | None = None,
    compress: bool = True,
) -> BackupSnapshot:
    """Build (or accept) a dump, persist it with metadata, and return the row.

    Sets checksum (sha256 of the stored bytes), size, schema version and
    compression flag so the snapshot is independently verifiable later.
    """
    if data is None:
        data = build_hostel_dump(hostel)
    schema_version = int(data.get("schema_version", BACKUP_SCHEMA_VERSION))

    payload = json.dumps(data, default=str).encode("utf-8")
    stored = gzip_bytes(payload) if compress else payload

    snap = BackupSnapshot(
        hostel=hostel,
        kind=kind,
        period=period,
        note=note[:255],
        schema_version=schema_version,
        checksum=sha256_hex(stored),
        size_bytes=len(stored),
        compressed=compress,
    )
    filename = build_filename(hostel, period, schema_version, compressed=compress)
    snap.file.save(filename, ContentFile(stored))
    snap.save()
    return snap
