"""Apply the backup retention policy (delete expired backups).

    python manage.py dr_retention
    python manage.py dr_retention --dry-run
"""

from django.core.management.base import BaseCommand

from apps.backups.models import BackupSnapshot
from apps.backups.retention import MANAGED_PERIODS, apply_retention, default_policy, storage_usage
from apps.tenants.models import Hostel


class Command(BaseCommand):
    help = "Enforce backup retention; deletes expired daily/weekly/monthly backups."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report only; delete nothing")

    def handle(self, *args, **opts):
        policy = default_policy()
        self.stdout.write(f"Retention policy: {policy}")

        if opts["dry_run"]:
            total = 0
            for hostel in Hostel.objects.all():
                for period in MANAGED_PERIODS:
                    keep = int(policy.get(period, 0) or 0)
                    qs = BackupSnapshot.objects.filter(hostel=hostel, period=period).order_by(
                        "-created_at"
                    )
                    stale = qs[keep:] if keep > 0 else qs
                    n = stale.count()
                    if n:
                        total += n
                        self.stdout.write(f"  {hostel.code} {period}: would delete {n}")
            self.stdout.write(self.style.WARNING(f"DRY RUN: would delete {total} backup(s)."))
            self.stdout.write(f"Storage: {storage_usage()}")
            return

        summary = apply_retention(policy)
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {summary['deleted']} backup(s), {summary['failed']} failure(s)."
            )
        )
        self.stdout.write(f"Storage: {summary['storage']}")
