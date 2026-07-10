"""Periodic custom-domain health: DNS re-validation + SSL monitoring.

Scheduled via Celery beat (see CELERY_BEAT_SCHEDULE). Domains whose
verification records disappear are flagged (not auto-deactivated — DNS blips
must not take a customer's site down); expiring/expired certificates raise
audit events so admins get alerted.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="domains.revalidate")
def revalidate_custom_domains():
    from apps.auditlog.models import AuditEvent
    from .models import CustomDomain
    from .services import check_dns, check_ssl

    checked = issues = 0
    for record in CustomDomain.objects.filter(status=CustomDomain.Status.ACTIVE):
        checked += 1
        try:
            health = check_dns(record)
            check_ssl(record)
            problems = []
            if not (health.get("txt") or health.get("cname")):
                problems.append("verification records missing")
            if record.ssl_status in (CustomDomain.SslStatus.EXPIRING,
                                     CustomDomain.SslStatus.EXPIRED):
                problems.append(f"certificate {record.ssl_status}")
            if problems:
                issues += 1
                AuditEvent.objects.create(
                    hostel_id=record.hostel_id,
                    action=AuditEvent.Action.UPDATE,
                    entity_type="custom_domain",
                    entity_id=str(record.hostel_id),
                    message=f"Domain health warning: {record.domain} — {'; '.join(problems)}",
                    meta={"domain": record.domain, "problems": problems},
                )
        except Exception:
            logger.exception("domain revalidation failed for %s", record.domain)
    logger.info("domain revalidation: %s checked, %s with issues", checked, issues)
    return {"checked": checked, "issues": issues}
