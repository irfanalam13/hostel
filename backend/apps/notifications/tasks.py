"""Celery tasks for the notification engine.

* ``dispatch_notification_task``  – async fan-out for one notification.
* ``send_scheduled_notifications``– beat: dispatch notifications whose time came.
* ``retry_failed_deliveries``     – beat: re-attempt failed pushes (backoff).
* ``prune_expired_subscriptions`` – beat: drop dead/stale subscriptions.

Scheduling is registered in ``CELERY_BEAT_SCHEDULE`` (settings).
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("apps.notifications")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def dispatch_notification_task(self, notification_id, user_ids=None):
    from .models import Notification
    from .services import dispatch

    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        logger.warning("dispatch_notification_task: notification %s not found", notification_id)
        return {"dispatched": False, "reason": "not_found"}

    stats = dispatch(notification, explicit_user_ids=user_ids or None)
    logger.info("dispatched notification %s: %s", notification_id, stats)
    return {"dispatched": True, **stats}


@shared_task
def send_scheduled_notifications():
    """Dispatch any SCHEDULED notification whose ``scheduled_at`` has passed."""
    from .models import Notification, NotificationStatus
    from .services import dispatch

    due = Notification.objects.filter(
        status=NotificationStatus.SCHEDULED, scheduled_at__lte=timezone.now()
    )
    count = 0
    for notification in due:
        try:
            dispatch(notification)
            count += 1
        except Exception:  # noqa: BLE001 - one bad notification shouldn't stop the rest
            logger.exception("failed to dispatch scheduled notification %s", notification.id)
    if count:
        logger.info("send_scheduled_notifications dispatched %s notification(s)", count)
    return count


@shared_task
def retry_failed_deliveries():
    from .services import retry_pending_deliveries

    n = retry_pending_deliveries()
    if n:
        logger.info("retried %s failed delivery attempt(s)", n)
    return n


@shared_task
def prune_expired_subscriptions(days_inactive: int = 60):
    """Delete inactive subscriptions and ones unused for a long time."""
    from datetime import timedelta

    from .models import PushSubscription

    cutoff = timezone.now() - timedelta(days=days_inactive)
    qs = PushSubscription.objects.filter(is_active=False)
    stale = PushSubscription.objects.filter(
        is_active=True, last_used_at__lt=cutoff, failure_count__gte=5
    )
    deleted = qs.count() + stale.count()
    qs.delete()
    stale.delete()
    if deleted:
        logger.info("pruned %s expired/stale push subscription(s)", deleted)
    return deleted
