"""Verify backups land OFF-HOST, not on the same disk as the database.

DEVOPS_AUDIT P1: if backups sit on the app/DB host, losing that host loses both
the data and its backups. Backups must go to remote object storage
(``STORAGE_BACKEND=s3`` → S3 / R2 / MinIO). This command inspects the storage
backend the snapshot ``FileField`` actually uses and, in production, FAILS if it
is local — so a misconfigured deploy is caught by a health check, not a disaster.

    python manage.py dr_offsite_check            # fail if on-host (prod) / warn (dev)
    python manage.py dr_offsite_check --strict   # always fail if on-host
    python manage.py dr_offsite_check --max-age-hours 26  # also assert a fresh backup exists
"""
import json

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now

from apps.backups.models import BackupSnapshot


def _storage_kind() -> tuple[str, bool]:
    """Return (dotted_class, is_offsite). Off-site = not local filesystem."""
    storage = BackupSnapshot._meta.get_field("file").storage or default_storage
    cls = type(storage)
    dotted = f"{cls.__module__}.{cls.__qualname__}"
    local = cls.__name__ == "FileSystemStorage" or "filesystem" in dotted.lower()
    return dotted, not local


class Command(BaseCommand):
    help = "Verify backups are stored off-host (remote object storage)."

    def add_arguments(self, parser):
        parser.add_argument("--strict", action="store_true",
                            help="Fail if on-host regardless of DEBUG (default: fail only in prod).")
        parser.add_argument("--max-age-hours", type=float, default=None,
                            help="Also require the newest backup to be younger than this.")

    def handle(self, *args, **opts):
        dotted, offsite = _storage_kind()
        report = {
            "storage_backend": dotted,
            "offsite": offsite,
            "storage_backend_env": getattr(settings, "STORAGE_BACKEND", "local"),
        }

        newest = BackupSnapshot.objects.order_by("-created_at").first()
        if opts["max_age_hours"] is not None:
            if newest is None:
                report["fresh_backup"] = False
                report["age_hours"] = None
            else:
                age_h = (now() - newest.created_at).total_seconds() / 3600
                report["age_hours"] = round(age_h, 2)
                report["fresh_backup"] = age_h <= opts["max_age_hours"]

        self.stdout.write(json.dumps(report, indent=2))

        problems = []
        must_be_offsite = opts["strict"] or not settings.DEBUG
        if not offsite and must_be_offsite:
            problems.append("backups are stored ON-HOST (local filesystem) — set STORAGE_BACKEND=s3.")
        elif not offsite:
            self.stdout.write(self.style.WARNING("On-host storage (dev) — set STORAGE_BACKEND=s3 for prod."))
        if opts["max_age_hours"] is not None and not report.get("fresh_backup"):
            problems.append(f"no backup younger than {opts['max_age_hours']}h (RPO risk).")

        if problems:
            raise CommandError("Offsite check FAILED: " + "; ".join(problems))
        self.stdout.write(self.style.SUCCESS("Offsite backup check passed."))
