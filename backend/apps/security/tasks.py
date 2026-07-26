"""Celery tasks: async event persistence + retention."""
import logging

from celery import shared_task

logger = logging.getLogger("apps.security")


@shared_task(name="apps.security.tasks.persist_security_event",
             ignore_result=True, max_retries=2, default_retry_delay=5)
def persist_security_event(payload: dict) -> None:
    from .events import persist_now

    persist_now(payload)


@shared_task(name="apps.security.tasks.prune_security_events", ignore_result=True)
def prune_security_events() -> int:
    """Delete events older than the configured retention window and reap
    expired temporary IP rules. Scheduled daily via Celery beat."""
    from datetime import timedelta

    from django.utils import timezone

    from .conf import get_config
    from .models import IPRule, SecurityEvent

    days = int(get_config().get("events.retention_days", 90) or 90)
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = SecurityEvent.objects.filter(created_at__lt=cutoff).delete()

    reaped, _ = IPRule.objects.filter(
        expires_at__isnull=False, expires_at__lt=timezone.now()
    ).delete()

    logger.info("security retention: %s events pruned, %s expired IP rules reaped",
                deleted, reaped)
    return deleted
