"""Celery tasks for audit-event persistence and retention.

``record_event`` runs in the request/response hot path (middleware logs every
API write and every 401/403), so the INSERT is offloaded to a worker. The
caller falls back to a synchronous write if the broker is unreachable, so no
event is ever lost to a queueing failure.
"""
import logging

from celery import shared_task

logger = logging.getLogger("apps.auditlog")


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def persist_audit_event(self, payload: dict):
    """Insert one hash-chained AuditEvent row from a serializable payload."""
    from .models import AuditEvent

    try:
        AuditEvent.objects.create_chained(**payload)
    except Exception as exc:  # noqa: BLE001 — retry transient DB errors
        logger.warning("audit event persist failed (attempt %s): %s",
                       self.request.retries + 1, exc)
        raise self.retry(exc=exc)
    return {"saved": True}


@shared_task
def prune_audit_events():
    """Archive-then-delete audit events beyond the retention window (beat task)."""
    from .retention import prune_expired

    summary = prune_expired()
    logger.info("audit retention run: %s", summary)
    return summary
