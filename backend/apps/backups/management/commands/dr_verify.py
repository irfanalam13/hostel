"""Validate stored backups (checksum, schema, required tables, readability).

    python manage.py dr_verify --backup-id <uuid>
    python manage.py dr_verify --all
    python manage.py dr_verify --hostel H-ABC123
"""

from django.core.management.base import BaseCommand, CommandError

from apps.backups.models import BackupSnapshot
from apps.backups.validation import validate_backup


class Command(BaseCommand):
    help = "Verify the integrity/validity of stored backups."

    def add_arguments(self, parser):
        parser.add_argument("--backup-id", help="Validate a single backup by UUID")
        parser.add_argument("--hostel", help="Validate all backups for a hostel code")
        parser.add_argument("--all", action="store_true", help="Validate every backup")

    def handle(self, *args, **opts):
        if opts["backup_id"]:
            qs = BackupSnapshot.objects.filter(id=opts["backup_id"])
        elif opts["hostel"]:
            qs = BackupSnapshot.objects.filter(hostel__code=opts["hostel"])
        elif opts["all"]:
            qs = BackupSnapshot.objects.all()
        else:
            raise CommandError("Provide --backup-id, --hostel or --all.")

        total = ok = 0
        for snap in qs.iterator():
            total += 1
            report = validate_backup(snap, persist=True)
            if report["ok"]:
                ok += 1
                self.stdout.write(f"  {snap.id} [{snap.period}] OK")
            else:
                self.stdout.write(
                    self.style.ERROR(f"  {snap.id} [{snap.period}] INVALID: {report['errors']}")
                )
        if total == 0:
            self.stdout.write(self.style.WARNING("No backups matched."))
        else:
            style = self.style.SUCCESS if ok == total else self.style.WARNING
            self.stdout.write(style(f"{ok}/{total} backups valid."))
