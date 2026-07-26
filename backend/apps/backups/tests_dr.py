"""Phase-4 disaster-recovery tests.

Covers the required scenarios:
  * Backup -> Restore -> data-consistency check
  * Corrupted backup handling (rejected)
  * Dry-run restore (no mutation)
  * Partial-failure recovery (atomic rollback leaves original data intact)
  * Retention policy enforcement (+ manual/pre-restore exemption)
  * Maintenance mode (read-only) enforcement
  * Schema-version incompatibility rejection
  * Admin restore API protection
"""

import json
import tempfile
from datetime import date
from decimal import Decimal
from unittest import mock

from django.test import RequestFactory, TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import User, UserHostel
from apps.attendance.models import Attendance
from apps.billing.models import Invoice, LedgerEntry, MonthlyDue, Payment, VacateRequest
from apps.hostel.models import Bed, Room
from apps.residents.models import BedAssignmentHistory, Resident, Stay
from apps.tenants.models import Hostel

from .admin_api import AdminRestoreView
from .dr import get_mode, set_mode
from .middleware import DRModeMiddleware
from .models import BackupPeriod, BackupSnapshot, DRMode, DRState, RestoreRun
from .restore import (
    RestoreError,
    RestoreValidationError,
    restore_hostel,
)
from .retention import apply_retention
from .storage import create_snapshot
from .validation import validate_backup

_TMP_MEDIA = tempfile.mkdtemp(prefix="dr-tests-")


def _populate(hostel):
    """Create one row in every canonical section for a hostel."""
    room = Room.objects.create(hostel=hostel, number="101")
    bed = Bed.objects.create(hostel=hostel, room=room, label="A")
    resident = Resident.objects.create(
        hostel=hostel, full_name="Asha R.", current_bed=bed, monthly_fee=Decimal("5000.00")
    )
    BedAssignmentHistory.objects.create(hostel=hostel, resident=resident, bed=bed)
    Stay.objects.create(resident=resident, bed=bed, check_in=date(2026, 1, 1))
    due = MonthlyDue.objects.create(
        hostel=hostel, resident=resident, year=2026, month=6, amount=Decimal("5000.00")
    )
    Payment.objects.create(hostel=hostel, resident=resident, due=due, amount=Decimal("2000.00"))
    inv = Invoice.objects.create(resident=resident, month=date(2026, 6, 1), amount=Decimal("5000.00"))
    LedgerEntry.objects.create(resident=resident, invoice=inv, amount=Decimal("2000.00"), entry_type="payment")
    VacateRequest.objects.create(resident=resident, requested_date=date(2026, 6, 10))
    Attendance.objects.create(hostel=hostel, resident=resident, date=date(2026, 6, 1))
    return resident


@override_settings(MEDIA_ROOT=_TMP_MEDIA)
class BackupRestoreCycleTests(TestCase):
    def setUp(self):
        self.hostel = Hostel.objects.create(name="DR Hostel")
        self.resident = _populate(self.hostel)

    def test_backup_restore_data_consistency(self):
        snap = create_snapshot(self.hostel, period=BackupPeriod.MANUAL)
        self.assertTrue(validate_backup(snap)["ok"])

        # Simulate data loss: wipe canonical data for the hostel.
        Resident.objects.filter(hostel=self.hostel).delete()  # cascades dues/payments/etc.
        Bed.objects.filter(hostel=self.hostel).delete()
        Room.objects.filter(hostel=self.hostel).delete()
        self.assertEqual(Resident.objects.filter(hostel=self.hostel).count(), 0)

        run = restore_hostel(self.hostel, source_snapshot=snap, force=True)

        self.assertEqual(run.status, RestoreRun.Status.COMPLETED)
        self.assertEqual(Resident.objects.filter(hostel=self.hostel).count(), 1)
        self.assertEqual(MonthlyDue.objects.filter(hostel=self.hostel).count(), 1)
        self.assertEqual(Payment.objects.filter(hostel=self.hostel).count(), 1)
        self.assertEqual(Attendance.objects.filter(hostel=self.hostel).count(), 1)
        r = Resident.objects.get(hostel=self.hostel)
        self.assertEqual(r.full_name, "Asha R.")
        self.assertEqual(r.monthly_fee, Decimal("5000.00"))
        # Relationships preserved (payment -> due, ledger -> invoice).
        self.assertIsNotNone(Payment.objects.get(hostel=self.hostel).due_id)
        self.assertTrue(run.stats["integrity"]["ok"])
        # A pre-restore snapshot was always taken.
        self.assertIsNotNone(run.pre_restore_snapshot_id)

    def test_restore_creates_pre_restore_snapshot(self):
        snap = create_snapshot(self.hostel, period=BackupPeriod.MANUAL)
        before = BackupSnapshot.objects.filter(period=BackupPeriod.PRE_RESTORE).count()
        restore_hostel(self.hostel, source_snapshot=snap, force=True)
        after = BackupSnapshot.objects.filter(period=BackupPeriod.PRE_RESTORE).count()
        self.assertEqual(after, before + 1)

    def test_dry_run_changes_nothing(self):
        snap = create_snapshot(self.hostel, period=BackupPeriod.MANUAL)
        Resident.objects.create(hostel=self.hostel, full_name="Temp Extra")
        live_before = Resident.objects.filter(hostel=self.hostel).count()

        run = restore_hostel(self.hostel, source_snapshot=snap, dry_run=True)

        self.assertEqual(run.status, RestoreRun.Status.DRY_RUN)
        self.assertEqual(Resident.objects.filter(hostel=self.hostel).count(), live_before)
        self.assertIn("plan", run.stats)
        self.assertEqual(run.stats["plan"]["would_insert"]["residents"], 1)

    def test_restore_without_force_is_refused(self):
        snap = create_snapshot(self.hostel, period=BackupPeriod.MANUAL)
        with self.assertRaises(RestoreError):
            restore_hostel(self.hostel, source_snapshot=snap, force=False, dry_run=False)
        # Original data untouched.
        self.assertEqual(Resident.objects.filter(hostel=self.hostel).count(), 1)

    def test_partial_failure_rolls_back(self):
        """A failure mid-restore must abort atomically and preserve original data.

        We force the in-transaction integrity check to fail (the same code path a
        real DB constraint violation triggers) and assert the delete+insert is
        rolled back, the run is marked failed, and the system returns to normal.
        """
        snap = create_snapshot(self.hostel, period=BackupPeriod.MANUAL)
        original_due_id = Payment.objects.get(hostel=self.hostel).due_id

        bad = {"ok": False, "live_counts": {}, "mismatches": {"residents": {"expected": 1, "actual": 0}}}
        with mock.patch("apps.backups.restore._integrity_check", return_value=bad):
            with self.assertRaises(RestoreError):
                restore_hostel(self.hostel, source_snapshot=snap, force=True)

        # Atomic rollback: the original, intact data is still present & unchanged.
        self.assertEqual(Resident.objects.filter(hostel=self.hostel).count(), 1)
        self.assertEqual(Payment.objects.filter(hostel=self.hostel).count(), 1)
        self.assertEqual(Payment.objects.get(hostel=self.hostel).due_id, original_due_id)
        # Run recorded as failed; system returned to normal mode.
        self.assertEqual(RestoreRun.objects.latest("created_at").status, RestoreRun.Status.FAILED)
        self.assertEqual(get_mode(), DRMode.NORMAL)


@override_settings(MEDIA_ROOT=_TMP_MEDIA)
class ValidationTests(TestCase):
    def setUp(self):
        self.hostel = Hostel.objects.create(name="Validate Hostel")
        _populate(self.hostel)

    def test_valid_backup_passes(self):
        snap = create_snapshot(self.hostel, period=BackupPeriod.MANUAL)
        report = validate_backup(snap)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["checks"]["checksum_match"], True)

    def test_checksum_mismatch_detected(self):
        snap = create_snapshot(self.hostel, period=BackupPeriod.MANUAL)
        snap.checksum = "deadbeef" * 8  # wrong checksum
        snap.save(update_fields=["checksum"])
        report = validate_backup(snap)
        self.assertFalse(report["ok"])
        self.assertFalse(report["checks"]["checksum_match"])

    def test_corrupt_unparseable_backup_rejected(self):
        report = validate_backup(raw_bytes=b"\x1f\x8b not really gzip")
        self.assertFalse(report["ok"])
        self.assertFalse(report["checks"].get("readable", False))

    def test_missing_required_tables_rejected(self):
        payload = json.dumps({"schema_version": 2, "residents": []}).encode()
        report = validate_backup(raw_bytes=payload)
        self.assertFalse(report["ok"])
        self.assertFalse(report["checks"]["required_tables_present"])

    def test_incompatible_schema_version_rejected(self):
        data = {"schema_version": 999}
        for s in ("residents", "monthly_dues", "billing_payments", "attendance", "hostel_rooms", "hostel_beds"):
            data[s] = []
        report = validate_backup(raw_bytes=json.dumps(data).encode())
        self.assertFalse(report["ok"])
        self.assertFalse(report["checks"]["schema_compatible"])

    def test_corrupt_backup_blocks_restore(self):
        snap = create_snapshot(self.hostel, period=BackupPeriod.MANUAL)
        snap.checksum = "0" * 64
        snap.save(update_fields=["checksum"])
        with self.assertRaises(RestoreValidationError):
            restore_hostel(self.hostel, source_snapshot=snap, force=False)


@override_settings(
    MEDIA_ROOT=_TMP_MEDIA,
    BACKUP_RETENTION={"daily": 2, "weekly": 1, "monthly": 1},
)
class RetentionTests(TestCase):
    def setUp(self):
        self.hostel = Hostel.objects.create(name="Retention Hostel")
        _populate(self.hostel)

    def test_retention_keeps_only_n_recent(self):
        for _ in range(5):
            create_snapshot(self.hostel, period=BackupPeriod.DAILY)
        manual = create_snapshot(self.hostel, period=BackupPeriod.MANUAL)

        summary = apply_retention()

        self.assertEqual(
            BackupSnapshot.objects.filter(hostel=self.hostel, period=BackupPeriod.DAILY).count(), 2
        )
        self.assertEqual(summary["deleted"], 3)
        # Manual backups are never auto-deleted.
        self.assertTrue(BackupSnapshot.objects.filter(id=manual.id).exists())

    def test_pre_restore_snapshots_are_exempt(self):
        for _ in range(3):
            create_snapshot(self.hostel, period=BackupPeriod.PRE_RESTORE)
        apply_retention()
        self.assertEqual(
            BackupSnapshot.objects.filter(period=BackupPeriod.PRE_RESTORE).count(), 3
        )


class MaintenanceModeTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.passed = {"called": False}

        def get_response(request):
            self.passed["called"] = True
            from django.http import HttpResponse

            return HttpResponse("ok")

        self.mw = DRModeMiddleware(get_response)

    def tearDown(self):
        DRState.set_mode(DRMode.NORMAL)

    def test_normal_mode_allows_writes(self):
        set_mode(DRMode.NORMAL)
        resp = self.mw(self.rf.post("/api/residents/"))
        self.assertEqual(resp.status_code, 200)

    def test_maintenance_blocks_writes_allows_reads(self):
        set_mode(DRMode.MAINTENANCE, reason="restore")
        write = self.mw(self.rf.post("/api/residents/"))
        self.assertEqual(write.status_code, 503)
        self.assertEqual(json.loads(write.content)["mode"], "maintenance")
        read = self.mw(self.rf.get("/api/residents/"))
        self.assertEqual(read.status_code, 200)

    def test_maintenance_exempts_admin_dr_api(self):
        set_mode(DRMode.MAINTENANCE)
        resp = self.mw(self.rf.post("/api/admin/restore/"))
        self.assertEqual(resp.status_code, 200)  # passed through to view layer

    def test_emergency_locks_everything_except_exempt(self):
        set_mode(DRMode.EMERGENCY, reason="full restore")
        self.assertEqual(self.mw(self.rf.get("/api/dashboard/")).status_code, 503)
        self.assertEqual(self.mw(self.rf.get("/health/")).status_code, 200)
        self.assertEqual(self.mw(self.rf.post("/api/admin/restore/")).status_code, 200)


@override_settings(MEDIA_ROOT=_TMP_MEDIA)
class AdminRestoreAPITests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.hostel = Hostel.objects.create(name="API Hostel")
        _populate(self.hostel)
        self.snap = create_snapshot(self.hostel, period=BackupPeriod.MANUAL)
        self.admin = User.objects.create_user("admin1", password="x", role="ADMIN")
        UserHostel.objects.create(user=self.admin, hostel=self.hostel)
        self.warden = User.objects.create_user("warden1", password="x", role="WARDEN")

    def _call(self, user, payload):
        request = self.factory.post("/api/admin/restore/", payload, format="json")
        force_authenticate(request, user=user)
        return AdminRestoreView.as_view()(request)

    def test_non_admin_forbidden(self):
        resp = self._call(self.warden, {"backup_id": str(self.snap.id), "dry_run": True})
        self.assertEqual(resp.status_code, 403)

    def test_admin_dry_run_ok(self):
        resp = self._call(self.admin, {"backup_id": str(self.snap.id), "dry_run": True})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], RestoreRun.Status.DRY_RUN)

    def test_destructive_requires_force_and_confirm(self):
        # Missing force.
        r1 = self._call(self.admin, {"backup_id": str(self.snap.id)})
        self.assertEqual(r1.status_code, 400)
        # Force but wrong confirm token.
        r2 = self._call(self.admin, {"backup_id": str(self.snap.id), "force": True, "confirm": "WRONG"})
        self.assertEqual(r2.status_code, 400)
        # Correct force + confirm.
        r3 = self._call(
            self.admin,
            {"backup_id": str(self.snap.id), "force": True, "confirm": self.hostel.code},
        )
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.data["status"], RestoreRun.Status.COMPLETED)
