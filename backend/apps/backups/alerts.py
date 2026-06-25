"""Disaster-recovery alerting.

A single funnel for DR failures so they are never silent. Every alert:
  * logs at ERROR (always),
  * captures to Sentry when ``SENTRY_DSN`` is configured,
  * optionally emails ``DR_ALERT_EMAILS`` when SMTP is configured,
  * writes a DR audit event.

Alerting itself must never raise — a failure to alert must not mask the
original incident.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event

logger = logging.getLogger("apps.backups")


def dr_alert(event: str, message: str, *, level=logging.ERROR, hostel=None, meta=None, audit_action=None):
    """Raise a DR alert across all configured channels. Returns nothing."""
    meta = meta or {}
    text = f"[DR ALERT] {event}: {message}"
    logger.log(level, text, extra={"dr_event": event, "dr_meta": meta})

    # Sentry (only if installed + DSN set).
    try:
        if getattr(settings, "SENTRY_DSN", ""):
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                scope.set_tag("dr_event", event)
                for k, v in meta.items():
                    scope.set_extra(k, v)
                sentry_sdk.capture_message(text, level="error")
    except Exception:  # noqa: BLE001
        logger.exception("DR alert: Sentry capture failed")

    # Email (best-effort).
    try:
        recipients = getattr(settings, "DR_ALERT_EMAILS", []) or []
        if recipients and getattr(settings, "EMAIL_HOST", ""):
            send_mail(
                subject=f"[Hostel DR] {event}",
                message=text,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=list(recipients),
                fail_silently=True,
            )
    except Exception:  # noqa: BLE001
        logger.exception("DR alert: email send failed")

    # Audit trail.
    try:
        record_event(
            action=audit_action or AuditEvent.Action.BACKUP_FAILED,
            hostel=hostel,
            entity_type="dr.alert",
            message=text,
            meta=meta,
        )
    except Exception:  # noqa: BLE001
        logger.exception("DR alert: audit write failed")
