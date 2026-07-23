"""Per-endpoint latency + query-count benchmark through the FULL middleware stack.

Seeds a throwaway tenant with a realistic amount of data, then times each API
endpoint with the in-process DRF test client (which shares the DB connection, so
the seed data is visible) and rolls the whole thing back — the database is left
untouched.

    docker compose exec -T web python manage.py benchmark_api
    docker compose exec -T web python manage.py benchmark_api --residents 200 --samples 15

Guards:
  * ``--max-queries`` (default 12): any 200 endpoint above this fails the run
    (exit 1) — a standing N+1 regression detector.
  * ``--slo-ms`` (default 100): any 200 endpoint whose median exceeds this fails.

This is the validation harness for the API-performance audit; wire it into CI to
keep the <100ms budget from silently regressing.
"""
import logging
import time
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext

ENDPOINTS = [
    ("residents", "/api/residents/"),
    ("stays", "/api/residents/stays/"),
    ("billing-dues", "/api/billing/dues/"),
    ("billing-payments", "/api/billing/payments/"),
    ("rooms", "/api/hostel/rooms/"),
    ("beds", "/api/hostel/beds/"),
    ("dashboard-owner", "/api/dashboard/owner/"),
    ("dashboard-sysstatus", "/api/dashboard/system-status/"),
    ("auth-me", "/api/auth/me/"),
    ("notices", "/api/notices/"),
    ("attendance", "/api/attendance/"),
    ("complaints", "/api/complaints/"),
    ("notifications", "/api/notifications/"),
    ("audit", "/api/audit/"),
]


class Command(BaseCommand):
    help = "Benchmark API endpoint latency + query counts through the full middleware stack."

    def add_arguments(self, parser):
        parser.add_argument("--residents", type=int, default=50)
        parser.add_argument("--samples", type=int, default=9)
        parser.add_argument("--max-queries", type=int, default=12)
        parser.add_argument("--slo-ms", type=float, default=100.0)

    def handle(self, *args, **opts):
        logging.disable(logging.INFO)  # silence per-request log spam during timing
        if "testserver" not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append("testserver")

        from django.core.cache import cache
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        from apps.accounts.models import User, UserHostel
        from apps.billing.models import MonthlyDue, Payment
        from apps.hostel.models import Bed, Room
        from apps.residents.models import Resident
        from apps.tenants.models import Hostel

        n_res = opts["residents"]
        n_samples = opts["samples"]
        cache.clear()

        failed = False
        with transaction.atomic():
            hostel = Hostel.objects.create(name="ZZ Bench Hostel")
            user = User.objects.create(
                username="zz_bench_user", email="zzbench@example.com", role="OWNER"
            )
            user.set_password("TestPass!234")
            user.save()
            UserHostel.objects.create(user=user, hostel=hostel, is_active=True)

            rooms = [Room.objects.create(hostel=hostel, number=f"ZR{i}", floor="1") for i in range(10)]
            beds = [
                Bed.objects.create(hostel=hostel, room=rooms[i % 10], label=f"ZB{i}")
                for i in range(30)
            ]
            residents = [
                Resident.objects.create(
                    hostel=hostel,
                    full_name=f"ZResident {i}",
                    phone=f"9800{i:06d}",
                    monthly_fee=Decimal("5000.00"),
                    current_bed=beds[i % 30],
                )
                for i in range(n_res)
            ]
            for r in residents:
                for m in range(1, 4):
                    MonthlyDue.objects.create(
                        hostel=hostel, resident=r, year=2026, month=m, amount=Decimal("5000.00")
                    )
                Payment.objects.create(
                    hostel=hostel, resident=r, amount=Decimal("5000.00"), method="cash"
                )

            refresh = RefreshToken.for_user(user)
            refresh["hostel_id"] = str(hostel.id)
            refresh["hostel_code"] = hostel.code
            refresh["role"] = user.role
            access = str(refresh.access_token)

            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}", HTTP_X_HOSTEL_CODE=hostel.code)

            self.stdout.write(
                f"\n===== ENDPOINT BENCHMARK ({n_res} residents, {n_res * 3} dues, "
                f"{n_res} payments) ====="
            )
            self.stdout.write(f"{'endpoint':<20}{'status':>7}{'queries':>9}{'best_ms':>10}{'med_ms':>10}")
            results = []
            for name, url in ENDPOINTS:
                client.get(url)  # warm caches
                with CaptureQueriesContext(connection) as ctx:
                    first = client.get(url)
                nq = len(ctx.captured_queries)
                samples = []
                for _ in range(n_samples):
                    t0 = time.perf_counter()
                    client.get(url)
                    samples.append((time.perf_counter() - t0) * 1000)
                samples.sort()
                med = samples[len(samples) // 2]
                best = samples[0]
                results.append((name, first.status_code, nq, best, med))
                self.stdout.write(f"{name:<20}{first.status_code:>7}{nq:>9}{best:>10.1f}{med:>10.1f}")
            self.stdout.write("=" * 68)

            offenders = [r for r in results if r[1] == 200 and r[2] > opts["max_queries"]]
            slow = [r for r in results if r[1] == 200 and r[4] > opts["slo_ms"]]
            if offenders:
                failed = True
                self.stdout.write(self.style.ERROR(
                    f"QUERY OFFENDERS (> {opts['max_queries']}): "
                    + ", ".join(f"{o[0]}={o[2]}" for o in offenders)
                ))
            else:
                self.stdout.write(self.style.SUCCESS("QUERY OFFENDERS: none"))
            if slow:
                failed = True
                self.stdout.write(self.style.ERROR(
                    f"SLOW (> {opts['slo_ms']:.0f}ms median): "
                    + ", ".join(f"{s[0]}={s[4]:.1f}ms" for s in slow)
                ))
            else:
                self.stdout.write(self.style.SUCCESS(f"SLO (< {opts['slo_ms']:.0f}ms median): all pass"))

            transaction.set_rollback(True)  # never persist benchmark data

        if failed:
            raise SystemExit(1)
