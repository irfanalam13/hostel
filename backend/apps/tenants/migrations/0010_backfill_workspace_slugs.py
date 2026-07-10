"""Backfill the permanent workspace username (slug) for pre-existing hostels.

Self-contained on purpose: reserved names and slug rules are snapshotted here
rather than imported from app code, so the migration's behavior can never
drift as the application evolves.
"""
import re

from django.db import migrations
from django.utils.text import slugify

_VALID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_MAX_LEN = 32

# Snapshot of the reserved list at the time this migration was written.
_RESERVED = {
    "admin", "api", "www", "mail", "root", "dashboard", "system", "support",
    "login", "auth", "docs", "static", "media", "assets", "cdn", "status",
    "health", "monitor", "test", "app", "staging", "dev", "demo", "internal",
    "billing", "smtp", "imap", "pop", "ftp", "ns1", "ns2", "webmail",
    "signup", "register", "account", "accounts", "security", "help", "blog",
}


def _candidate(name, code):
    base = slugify(name or "")[:_MAX_LEN].strip("-")
    if not base or not _VALID.match(base) or len(base) < 3:
        # Hostel codes are "HTL-XXXXXXXX" — lowercased they are valid labels.
        base = (code or "").lower().strip("-") or "hostel"
    return base


def backfill_slugs(apps, schema_editor):
    Hostel = apps.get_model("tenants", "Hostel")
    taken = set(
        Hostel.objects.exclude(slug__isnull=True).exclude(slug="").values_list("slug", flat=True)
    )
    for hostel in Hostel.objects.filter(slug__isnull=True).order_by("created_at"):
        base = _candidate(hostel.name, hostel.code)
        slug = base
        i = 2
        while slug in taken or slug in _RESERVED:
            suffix = f"-{i}"
            slug = base[: _MAX_LEN - len(suffix)].rstrip("-") + suffix
            i += 1
        hostel.slug = slug
        hostel.save(update_fields=["slug"])
        taken.add(slug)


def noop(apps, schema_editor):
    # Reverse: slugs are additive; leaving them in place is safe.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0009_hostel_currency_hostel_deleted_at_hostel_is_deleted_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_slugs, noop),
    ]
