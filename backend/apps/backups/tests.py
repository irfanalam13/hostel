from decimal import Decimal

from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from apps.billing.models import MonthlyDue
from apps.common.middleware import SecurityHeadersMiddleware
from apps.residents.models import Resident
from apps.tenants.models import Hostel

from .tasks import BACKUP_SCHEMA_VERSION, _dump_hostel


class BackupCoverageTests(TestCase):
    """P4: backups must include canonical Track-A data, not just legacy Track B."""

    def setUp(self):
        self.hostel = Hostel.objects.create(name="Coverage Hostel")
        self.resident = Resident.objects.create(hostel=self.hostel, full_name="Chandra P.")
        self.due = MonthlyDue.objects.create(
            hostel=self.hostel, resident=self.resident,
            year=2026, month=6, amount=Decimal("1500.00"),
        )

    def test_dump_includes_track_a_sections(self):
        dump = _dump_hostel(self.hostel)
        self.assertEqual(dump["schema_version"], BACKUP_SCHEMA_VERSION)
        for key in ("residents", "monthly_dues", "billing_payments", "invoices", "attendance"):
            self.assertIn(key, dump, f"backup missing Track-A section: {key}")
        self.assertEqual(len(dump["residents"]), 1)
        self.assertEqual(len(dump["monthly_dues"]), 1)
        # Legacy Track B sections still present (kept during migration).
        self.assertIn("students", dump)


class SecurityHeadersMiddlewareTests(TestCase):
    """P1: defence-in-depth response headers are always applied."""

    def _response(self):
        mw = SecurityHeadersMiddleware(lambda request: HttpResponse("ok"))
        return mw(RequestFactory().get("/api/anything/"))

    def test_referrer_and_permissions_always_set(self):
        resp = self._response()
        self.assertEqual(resp["Referrer-Policy"], "same-origin")
        self.assertIn("camera=()", resp["Permissions-Policy"])

    def test_csp_applied_when_not_debug(self):
        # The Django test runner forces DEBUG=False, so CSP should be present.
        resp = self._response()
        self.assertIn("default-src 'none'", resp["Content-Security-Policy"])
