"""Inspect or change the system disaster-recovery mode.

    python manage.py dr_mode                       # show current mode
    python manage.py dr_mode --set maintenance --reason "restoring H-ABC"
    python manage.py dr_mode --set normal
"""

from django.core.management.base import BaseCommand

from apps.backups.dr import get_mode, set_mode
from apps.backups.models import DRMode


class Command(BaseCommand):
    help = "Show or set the disaster-recovery mode (normal/maintenance/emergency)."

    def add_arguments(self, parser):
        parser.add_argument("--set", dest="mode", choices=DRMode.values, help="New mode")
        parser.add_argument("--reason", default="", help="Reason (audited)")

    def handle(self, *args, **opts):
        if not opts["mode"]:
            self.stdout.write(f"Current DR mode: {get_mode()}")
            return
        state = set_mode(opts["mode"], reason=opts["reason"])
        self.stdout.write(self.style.SUCCESS(f"DR mode set to: {state.mode} ({state.reason})"))
