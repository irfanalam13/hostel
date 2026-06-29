"""Celery task: retention pruning for analytics events."""
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("apps.analytics")


@shared_task
def prune_old_analytics():
    """Delete analytics events older than ANALYTICS_RETENTION_DAYS (default 90)."""
    from .models import AnalyticsEvent

    days = getattr(settings, "ANALYTICS_RETENTION_DAYS", 90)
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = AnalyticsEvent.objects.filter(created_at__lt=cutoff).delete()
    if deleted:
        logger.info("pruned %s analytics event(s) older than %s days", deleted, days)
    return deleted
