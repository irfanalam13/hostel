"""Archive-then-prune audit events beyond the retention window.

    python manage.py prune_audit_events                 # use AUDIT_RETENTION_DAYS
    python manage.py prune_audit_events --days 730
    python manage.py prune_audit_events --dry-run
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.auditlog.models import AuditChainState, AuditEvent
from apps.auditlog.retention import prune_expired


class Command(BaseCommand):
    help = "Archive and prune audit events older than the retention window."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=None,
                            help="Override AUDIT_RETENTION_DAYS.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would be pruned without deleting.")

    def handle(self, *args, **options):
        days = options.get("days")
        if days is None:
            days = int(getattr(settings, "AUDIT_RETENTION_DAYS", 365))

        if options["dry_run"]:
            from django.utils import timezone

            if days <= 0:
                self.stdout.write("Retention disabled (days <= 0); nothing would be pruned.")
                return
            cutoff = timezone.now() - timezone.timedelta(days=days)
            state = AuditChainState.load()
            count = AuditEvent.objects.filter(
                sequence__isnull=False,
                sequence__gt=state.checkpoint_sequence,
                created_at__lt=cutoff,
            ).count()
            self.stdout.write(f"[dry-run] {count} event(s) older than {days}d would be archived+pruned.")
            return

        summary = prune_expired(retention_days=days)
        self.stdout.write(self.style.SUCCESS(f"Retention run complete: {summary}"))
