"""Create a backup for one hostel (by code) or all active hostels.

    python manage.py dr_backup --all
    python manage.py dr_backup --hostel H-ABC123 --period manual
"""

from django.core.management.base import BaseCommand, CommandError

from apps.backups.models import BackupPeriod
from apps.backups.storage import create_snapshot
from apps.backups.validation import validate_backup
from apps.tenants.models import Hostel


class Command(BaseCommand):
    help = "Create a verified backup for one hostel or all active hostels."

    def add_arguments(self, parser):
        parser.add_argument("--hostel", help="Hostel code (e.g. H-ABC123)")
        parser.add_argument("--all", action="store_true", help="Back up all active hostels")
        parser.add_argument(
            "--period", default=BackupPeriod.MANUAL, choices=[c for c, _ in BackupPeriod.choices]
        )

    def handle(self, *args, **opts):
        if opts["all"]:
            hostels = list(Hostel.objects.filter(is_active=True))
        elif opts["hostel"]:
            hostels = list(Hostel.objects.filter(code=opts["hostel"]))
            if not hostels:
                raise CommandError(f"Hostel {opts['hostel']!r} not found.")
        else:
            raise CommandError("Provide --hostel <code> or --all.")

        for hostel in hostels:
            snap = create_snapshot(hostel, period=opts["period"], kind="manual", note="CLI backup")
            report = validate_backup(snap, persist=True)
            ok = "VALID" if report["ok"] else "INVALID: " + "; ".join(report["errors"])
            self.stdout.write(
                f"{hostel.code}: backup {snap.id} ({snap.size_bytes} B, "
                f"sha256={snap.checksum[:12]}…) [{ok}]"
            )
        self.stdout.write(self.style.SUCCESS(f"Done: {len(hostels)} backup(s)."))
