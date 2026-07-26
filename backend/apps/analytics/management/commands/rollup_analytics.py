"""Backfill / refresh analytics daily rollups.

    python manage.py rollup_analytics                 # refresh recent days
    python manage.py rollup_analytics --days 400       # backfill last 400 days
    python manage.py rollup_analytics --date 2026-07-01
"""
import datetime as dt

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.analytics.rollup import aggregate_day, aggregate_range


class Command(BaseCommand):
    help = "Recompute analytics daily rollups from raw events."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=2,
                            help="Refresh the last N days (default 2).")
        parser.add_argument("--date", type=str, default=None,
                            help="Recompute a single YYYY-MM-DD day.")

    def handle(self, *args, **options):
        if options["date"]:
            try:
                day = dt.date.fromisoformat(options["date"])
            except ValueError as exc:
                raise CommandError(f"Invalid --date: {exc}")
            written = aggregate_day(day)
            self.stdout.write(self.style.SUCCESS(f"Rolled up {written} row(s) for {day}."))
            return

        days = max(1, options["days"])
        today = timezone.localdate()
        written = aggregate_range(today - dt.timedelta(days=days - 1), today)
        self.stdout.write(self.style.SUCCESS(
            f"Rolled up {written} row(s) across the last {days} day(s)."
        ))
