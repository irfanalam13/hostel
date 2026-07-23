from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.residents.models import Resident
from apps.billing.models import MonthlyDue

class Command(BaseCommand):
    help = "Generate monthly dues for all active residents (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=None)
        parser.add_argument("--month", type=int, default=None)

    def handle(self, *args, **opts):
        now = timezone.now().date()
        year = opts["year"] or now.year
        month = opts["month"] or now.month

        created = 0
        qs = Resident.objects.filter(status__in=["active", "went_home"])
        for r in qs.iterator():
            if r.monthly_fee <= 0:
                continue
            obj, is_created = MonthlyDue.objects.get_or_create(
                hostel=r.hostel,
                resident=r,
                year=year,
                month=month,
                defaults={"amount": r.monthly_fee},
            )
            if is_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Generated dues: {created} for {year}-{month}"))