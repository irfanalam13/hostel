"""Verify the append-only audit hash chain.

    python manage.py verify_audit_chain          # verify whole surviving chain
    python manage.py verify_audit_chain --limit 1000

Exit code 0 = intact, 1 = tampering/gap detected (usable in CI / cron alerts).
"""
from django.core.management.base import BaseCommand

from apps.auditlog.integrity import verify_chain


class Command(BaseCommand):
    help = "Verify the integrity of the append-only audit hash chain."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Only verify the most recent N events (default: all).",
        )

    def handle(self, *args, **options):
        result = verify_chain(limit=options.get("limit"))
        if result.ok:
            self.stdout.write(self.style.SUCCESS(
                f"Audit chain intact — {result.checked} event(s) verified."
            ))
            return
        self.stderr.write(self.style.ERROR(
            f"Audit chain FAILED at sequence {result.first_bad_sequence}: "
            f"{result.reason}"
        ))
        for err in result.errors:
            self.stderr.write(f"  - {err}")
        raise SystemExit(1)
