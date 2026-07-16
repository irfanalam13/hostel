"""Run a restore-drill and grade it against RTO/RPO targets (Phase 5, §6).

    # latest backup for a specific hostel, default targets
    python manage.py dr_drill --hostel ACME --confirm

    # a specific snapshot with explicit targets (RTO 5m, RPO 26h)
    python manage.py dr_drill --snapshot <uuid> --max-rto 300 --max-rpo 93600 --confirm

Exits non-zero if the drill fails its targets — so a scheduled job / CI gate goes
red. Because it briefly enters maintenance mode and rewrites the target hostel's
canonical rows, it REFUSES to run without --confirm (or DR_DRILL_CONFIRM=1) and
is intended for an isolated / staging database.
"""
import json
import os

from django.core.management.base import BaseCommand, CommandError

from apps.backups.drill import latest_snapshot, run_drill
from apps.backups.models import BackupSnapshot


class Command(BaseCommand):
    help = "Restore a backup end-to-end and report RTO/RPO/integrity (isolated DB only)."

    def add_arguments(self, parser):
        parser.add_argument("--snapshot", help="BackupSnapshot id to restore (default: latest).")
        parser.add_argument("--hostel", help="Hostel code to pick the latest snapshot for.")
        parser.add_argument("--max-rto", type=float, default=None, help="RTO target (seconds).")
        parser.add_argument("--max-rpo", type=float, default=None, help="RPO target (seconds).")
        parser.add_argument("--keep", action="store_true", help="Keep the pre-restore snapshot.")
        parser.add_argument("--confirm", action="store_true",
                            help="Acknowledge this hits a maintenance window; required to run.")

    def handle(self, *args, **opts):
        if not (opts["confirm"] or os.getenv("DR_DRILL_CONFIRM") == "1"):
            raise CommandError(
                "dr_drill enters a maintenance window and rewrites the target hostel's rows. "
                "Run it against an ISOLATED/staging DB and pass --confirm (or DR_DRILL_CONFIRM=1)."
            )

        snap = None
        if opts["snapshot"]:
            try:
                snap = BackupSnapshot.objects.get(pk=opts["snapshot"])
            except BackupSnapshot.DoesNotExist as e:
                raise CommandError(f"Snapshot {opts['snapshot']} not found.") from e
        else:
            hostel = None
            if opts["hostel"]:
                from apps.tenants.models import Hostel
                try:
                    hostel = Hostel.objects.get(code=opts["hostel"])
                except Hostel.DoesNotExist as e:
                    raise CommandError(f"Hostel {opts['hostel']} not found.") from e
            snap = latest_snapshot(hostel)

        if snap is None:
            raise CommandError("No backup snapshot available to drill.")

        result = run_drill(
            snap,
            max_rto_seconds=opts["max_rto"],
            max_rpo_seconds=opts["max_rpo"],
            cleanup=not opts["keep"],
        )
        self.stdout.write(json.dumps(result, indent=2))
        if not result["ok"]:
            raise CommandError("DR drill FAILED: " + "; ".join(result["reasons"]))
        self.stdout.write(self.style.SUCCESS(
            f"DR drill PASSED — RTO {result['rto_seconds']}s, RPO {result['rpo_seconds']}s."
        ))
