"""Generate a security report from the command line / cron.

    python manage.py security_report --period weekly --format csv > report.csv
    python manage.py security_report --window 6 --format json
"""
import json

from django.core.management.base import BaseCommand

from apps.security import reports


class Command(BaseCommand):
    help = "Generate a security threat report (daily/weekly/monthly/custom)."

    def add_arguments(self, parser):
        parser.add_argument("--period", default="daily",
                            choices=["daily", "weekly", "monthly"])
        parser.add_argument("--window", type=int, default=None,
                            help="Window in hours (overrides --period).")
        parser.add_argument("--format", default="json", choices=["json", "csv"])
        parser.add_argument("--tenant", default=None, help="Scope to one tenant id.")

    def handle(self, *args, **options):
        data = reports.build(
            period=options["period"],
            window_hours=options["window"],
            tenant_id=options["tenant"],
        )
        if options["format"] == "csv":
            self.stdout.write(reports.to_csv(data))
        else:
            self.stdout.write(json.dumps(data, indent=2, default=str))
