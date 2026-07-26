"""Restore-drill tests (Phase 5, §6). Exercises the real engine on the test DB."""
import pytest

from apps.backups.drill import latest_snapshot, run_drill
from apps.backups.models import BackupSnapshot
from apps.backups.storage import create_snapshot

pytestmark = pytest.mark.django_db


def test_drill_restores_and_reports_rto_rpo(hostel, room, bed, resident):
    # A backup with real canonical rows (rooms/beds/residents).
    snap = create_snapshot(hostel, note="drill-test")

    result = run_drill(snap)

    assert result["ok"] is True, result["reasons"]
    assert result["integrity_ok"] is True
    assert result["rto_seconds"] >= 0
    assert result["rpo_seconds"] >= 0
    assert result["hostel"] == hostel.code
    # Data survived the delete+reinsert restore.
    from apps.residents.models import Resident
    assert Resident.objects.filter(hostel=hostel).exists()


def test_drill_fails_when_rto_target_exceeded(hostel, room, bed, resident):
    snap = create_snapshot(hostel)
    # An impossibly tight RTO target must fail the drill (not raise).
    result = run_drill(snap, max_rto_seconds=0.0)
    assert result["ok"] is False
    assert any("RTO" in r for r in result["reasons"])


def test_drill_fails_when_rpo_target_exceeded(hostel):
    snap = create_snapshot(hostel)
    result = run_drill(snap, max_rpo_seconds=-1)  # any real age exceeds -1
    assert result["ok"] is False
    assert any("RPO" in r for r in result["reasons"])


def test_drill_cleans_up_pre_restore_snapshot(hostel, room, bed, resident):
    create_snapshot(hostel)
    before = BackupSnapshot.objects.count()
    run_drill(latest_snapshot(hostel), cleanup=True)
    # Restore makes a pre-restore snapshot then the drill deletes it → net zero.
    assert BackupSnapshot.objects.count() == before
