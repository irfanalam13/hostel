"""Restore a hostel from a stored backup or a backup file on disk.

Disaster scenarios:
    # From a stored backup (DB still has the BackupSnapshot row):
    python manage.py dr_restore --backup-id <uuid> --dry-run
    python manage.py dr_restore --backup-id <uuid> --force --confirm <HOSTEL_CODE>

    # From a file alone, after TOTAL database loss (recreates the hostel):
    python manage.py dr_restore --file backups/daily/H-ABC_2026..._v2.json.gz \\
        --force --confirm <HOSTEL_CODE>
"""

from django.core.management.base import BaseCommand, CommandError

from apps.backups.models import BackupSnapshot
from apps.backups.restore import (
    RestoreError,
    ensure_hostel_from_dump,
    restore_hostel,
)
from apps.backups.storage import decode_backup_bytes, load_backup_data


class Command(BaseCommand):
    help = "Restore a hostel's canonical data from a backup (id or file)."

    def add_arguments(self, parser):
        parser.add_argument("--backup-id", help="BackupSnapshot UUID to restore from")
        parser.add_argument("--file", help="Path to a backup .json or .json.gz file")
        parser.add_argument("--dry-run", action="store_true", help="Validate + plan only")
        parser.add_argument("--force", action="store_true", help="Authorise destructive overwrite")
        parser.add_argument("--confirm", default="", help="Must equal the hostel code to overwrite")

    def handle(self, *args, **opts):
        backup_id, path = opts["backup_id"], opts["file"]
        dry_run, force = opts["dry_run"], opts["force"]

        if not backup_id and not path:
            raise CommandError("Provide --backup-id or --file.")

        snapshot = None
        data = None
        if backup_id:
            try:
                snapshot = BackupSnapshot.objects.select_related("hostel").get(id=backup_id)
            except BackupSnapshot.DoesNotExist:
                raise CommandError(f"Backup {backup_id} not found.")
            hostel = snapshot.hostel
            data = load_backup_data(snapshot)
        else:
            with open(path, "rb") as fh:
                data = decode_backup_bytes(fh.read())
            hostel = ensure_hostel_from_dump(data, create=True)
            if hostel is None:
                raise CommandError("Could not resolve a hostel from the backup file.")

        # Safety: destructive run requires force + confirmation token = hostel code.
        if not dry_run:
            if not force:
                raise CommandError("Destructive restore requires --force (or use --dry-run).")
            if opts["confirm"] != hostel.code:
                raise CommandError(
                    f"--confirm must equal the hostel code '{hostel.code}' to overwrite its data."
                )

        self.stdout.write(f"Restoring hostel {hostel.code} (dry_run={dry_run}, force={force})…")
        try:
            run = restore_hostel(
                hostel, source_snapshot=snapshot, data=None if snapshot else data,
                dry_run=dry_run, force=force,
            )
        except RestoreError as exc:
            raise CommandError(f"Restore failed: {exc}")

        self.stdout.write(f"  status: {run.status}")
        if run.pre_restore_snapshot_id:
            self.stdout.write(f"  pre-restore snapshot: {run.pre_restore_snapshot_id}")
        integ = run.stats.get("integrity")
        if integ is not None:
            self.stdout.write(f"  integrity ok: {integ['ok']}  counts: {integ['live_counts']}")
        plan = run.stats.get("plan")
        if plan is not None:
            self.stdout.write(f"  would insert: {plan['would_insert']}")
        self.stdout.write(self.style.SUCCESS("Done."))
