"""Phase 7 audit hardening — tamper-evidence, immutability, retention."""
import pytest
from django.db import connection

from apps.auditlog.integrity import verify_chain
from apps.auditlog.models import AuditChainState, AuditEvent, AuditImmutableError
from apps.auditlog.retention import prune_expired


def _make(n):
    for i in range(n):
        AuditEvent.objects.create_chained(
            action=AuditEvent.Action.CREATE,
            entity_type="resident",
            entity_id=str(i),
            message=f"created resident {i}",
            reason="test",
            changes={"old": None, "new": {"name": f"r{i}"}},
            meta={"n": i},
        )


@pytest.mark.django_db
def test_chain_builds_and_verifies():
    _make(5)
    head = AuditChainState.load()
    assert head.sequence == 5
    result = verify_chain()
    assert result.ok, result.as_dict()
    assert result.checked == 5
    seqs = list(AuditEvent.objects.order_by("sequence").values_list("sequence", flat=True))
    assert seqs == [1, 2, 3, 4, 5]


@pytest.mark.django_db
def test_events_are_immutable():
    _make(1)
    event = AuditEvent.objects.first()
    with pytest.raises(AuditImmutableError):
        event.message = "hacked"
        event.save()
    with pytest.raises(AuditImmutableError):
        event.delete()
    with pytest.raises(AuditImmutableError):
        AuditEvent.objects.all().delete()


@pytest.mark.django_db
def test_tamper_is_detected():
    _make(5)
    assert verify_chain().ok
    # Tamper by bypassing the ORM entirely (simulating a DB-level attacker).
    with connection.cursor() as cur:
        cur.execute("UPDATE auditlog_auditevent SET message = 'tampered' WHERE sequence = 3")
    result = verify_chain()
    assert not result.ok
    assert result.first_bad_sequence == 3


@pytest.mark.django_db
def test_deleting_newest_row_is_detected():
    _make(4)
    with connection.cursor() as cur:
        cur.execute("DELETE FROM auditlog_auditevent WHERE sequence = 4")
    result = verify_chain()
    assert not result.ok  # tip no longer matches recorded head


@pytest.mark.django_db
def test_retention_archives_and_tail_still_verifies(tmp_path, settings):
    settings.AUDIT_ARCHIVE_DIR = str(tmp_path)
    _make(5)
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE auditlog_auditevent SET created_at = %s WHERE sequence IN (1, 2)",
            ["2000-01-01 00:00:00+00:00"],
        )
    summary = prune_expired(retention_days=365)
    assert summary["deleted"] == 2
    assert summary["checkpoint_sequence"] == 2

    assert AuditEvent.objects.count() == 3
    result = verify_chain()
    assert result.ok, result.as_dict()
    assert result.checked == 3
    assert list(tmp_path.glob("audit-*.jsonl"))


@pytest.mark.django_db
def test_record_event_sync_path(settings):
    settings.AUDIT_LOG_ASYNC = False
    from apps.auditlog.services import record_event

    record_event(
        None,
        action=AuditEvent.Action.LOGIN,
        message="login ok",
        result=AuditEvent.Result.SUCCESS,
        status_code=200,
        request_id="abc123",
    )
    event = AuditEvent.objects.get()
    assert event.request_id == "abc123"
    assert event.status_code == 200
    assert event.sequence == 1
    assert verify_chain().ok
