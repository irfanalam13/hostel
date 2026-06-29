"""Notification engine: recipient resolution, Web Push delivery, retries.

Delivery uses the standard Web Push protocol with VAPID, which transparently
covers Chrome/Edge (FCM endpoints), Firefox (autopush) and Safari (Apple Push) —
no per-vendor code. ``pywebpush`` is imported lazily so the app loads even when
the dependency or VAPID keys are absent (delivery simply no-ops with a clear
log line).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import UserHostel

from .models import (
    AudienceType,
    DeliveryStatus,
    Notification,
    NotificationDelivery,
    NotificationRecipient,
    NotificationStatus,
    PushSubscription,
)

logger = logging.getLogger("apps.notifications")

MAX_RETRIES = getattr(settings, "NOTIFICATIONS_MAX_RETRIES", 3)
RETRY_BACKOFF_MINUTES = getattr(settings, "NOTIFICATIONS_RETRY_BACKOFF_MINUTES", (1, 5, 30))


# --------------------------------------------------------------------------- #
# VAPID / Web Push transport
# --------------------------------------------------------------------------- #
def push_enabled() -> bool:
    return bool(getattr(settings, "VAPID_PRIVATE_KEY", "") and getattr(settings, "VAPID_SUBJECT", ""))


def _vapid_kwargs() -> dict:
    return {
        "vapid_private_key": settings.VAPID_PRIVATE_KEY,
        "vapid_claims": {"sub": settings.VAPID_SUBJECT},
    }


class PushResult:
    """Outcome of a single push attempt."""

    def __init__(self, ok: bool, *, expired: bool = False, retryable: bool = False, error: str = ""):
        self.ok = ok
        self.expired = expired  # subscription is dead (404/410) — delete it
        self.retryable = retryable
        self.error = error


def send_web_push(subscription: PushSubscription, payload_json: str) -> PushResult:
    """Send one payload to one subscription. Never raises."""
    if not push_enabled():
        return PushResult(False, retryable=True, error="VAPID not configured")
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:  # pragma: no cover - dependency missing
        logger.error("pywebpush is not installed; cannot deliver push notifications")
        return PushResult(False, retryable=True, error="pywebpush not installed")

    try:
        webpush(
            subscription_info=subscription.as_subscription_info(),
            data=payload_json,
            timeout=10,
            **_vapid_kwargs(),
        )
        return PushResult(True)
    except WebPushException as exc:  # type: ignore[misc]
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (404, 410):
            return PushResult(False, expired=True, error=f"gone ({status})")
        if status in (429, 500, 502, 503, 504) or status is None:
            return PushResult(False, retryable=True, error=f"transient ({status}): {exc}")
        # 400/401/403/413 → permanent (bad VAPID, payload too big, etc.)
        return PushResult(False, error=f"permanent ({status}): {exc}")
    except Exception as exc:  # noqa: BLE001 - defensive: delivery must never crash dispatch
        return PushResult(False, retryable=True, error=str(exc))


# --------------------------------------------------------------------------- #
# Recipient resolution (tenant-aware)
# --------------------------------------------------------------------------- #
def resolve_recipient_user_ids(notification: Notification, explicit_user_ids=None) -> list[int]:
    """Return the user ids that should receive ``notification``.

    Always constrained to *active members of the notification's hostel*, so a
    notification can never leak across tenants.
    """
    members = UserHostel.objects.filter(
        hostel=notification.hostel, is_active=True
    ).values_list("user_id", flat=True)
    member_ids = set(members)

    if notification.audience == AudienceType.USER:
        ids = set(explicit_user_ids or [])
        return list(ids & member_ids)

    if notification.audience == AudienceType.ROLE:
        roles = [r.upper() for r in (notification.target_roles or [])]
        if not roles:
            return []
        from apps.accounts.models import User

        role_ids = User.objects.filter(id__in=member_ids, role__in=roles).values_list("id", flat=True)
        return list(role_ids)

    # AudienceType.ALL
    return list(member_ids)


@transaction.atomic
def build_recipients(notification: Notification, explicit_user_ids=None) -> int:
    """Create the per-user inbox rows. Idempotent (bulk_create ignores dupes)."""
    user_ids = resolve_recipient_user_ids(notification, explicit_user_ids)
    existing = set(
        NotificationRecipient.objects.filter(notification=notification).values_list("user_id", flat=True)
    )
    to_create = [
        NotificationRecipient(notification=notification, user_id=uid)
        for uid in user_ids
        if uid not in existing
    ]
    if to_create:
        NotificationRecipient.objects.bulk_create(to_create, ignore_conflicts=True)
    notification.recipients_count = NotificationRecipient.objects.filter(
        notification=notification
    ).count()
    notification.save(update_fields=["recipients_count", "updated_at"])
    return notification.recipients_count


# --------------------------------------------------------------------------- #
# Dispatch + delivery tracking
# --------------------------------------------------------------------------- #
def _backoff_for(attempt: int) -> timedelta:
    idx = min(max(attempt - 1, 0), len(RETRY_BACKOFF_MINUTES) - 1)
    return timedelta(minutes=RETRY_BACKOFF_MINUTES[idx])


def _attempt_delivery(delivery: NotificationDelivery, payload_json: str) -> None:
    sub = delivery.subscription
    delivery.attempts += 1
    delivery.last_attempt_at = timezone.now()

    if sub is None or not sub.is_active:
        delivery.status = DeliveryStatus.EXPIRED
        delivery.last_error = "subscription inactive"
        delivery.save(update_fields=["attempts", "last_attempt_at", "status", "last_error", "updated_at"])
        return

    result = send_web_push(sub, payload_json)
    if result.ok:
        delivery.status = DeliveryStatus.SENT
        delivery.last_error = ""
        delivery.next_retry_at = None
        sub.failure_count = 0
        sub.last_used_at = timezone.now()
        sub.save(update_fields=["failure_count", "last_used_at", "updated_at"])
        # Mark the recipient delivered.
        rec = delivery.recipient
        if not rec.delivered:
            rec.delivered = True
            rec.delivered_at = timezone.now()
            rec.save(update_fields=["delivered", "delivered_at", "updated_at"])
    elif result.expired:
        delivery.status = DeliveryStatus.EXPIRED
        delivery.last_error = result.error
        delivery.next_retry_at = None
        sub.is_active = False
        sub.save(update_fields=["is_active", "updated_at"])
    elif result.retryable and delivery.attempts < MAX_RETRIES:
        delivery.status = DeliveryStatus.FAILED
        delivery.last_error = result.error
        delivery.next_retry_at = timezone.now() + _backoff_for(delivery.attempts)
        sub.failure_count += 1
        sub.save(update_fields=["failure_count", "updated_at"])
    else:
        delivery.status = DeliveryStatus.FAILED
        delivery.last_error = result.error
        delivery.next_retry_at = None  # exhausted
        sub.failure_count += 1
        sub.save(update_fields=["failure_count", "updated_at"])

    delivery.save(
        update_fields=["attempts", "last_attempt_at", "status", "last_error", "next_retry_at", "updated_at"]
    )


def dispatch(notification: Notification, explicit_user_ids=None) -> dict:
    """Fan a notification out to every recipient's active subscriptions."""
    if notification.status in (NotificationStatus.SENT, NotificationStatus.SENDING):
        # Allow re-dispatch only of retryable failures via retry task; here, guard.
        pass

    if not NotificationRecipient.objects.filter(notification=notification).exists():
        build_recipients(notification, explicit_user_ids)

    notification.status = NotificationStatus.SENDING
    notification.save(update_fields=["status", "updated_at"])

    recipients = NotificationRecipient.objects.filter(notification=notification).select_related("user")
    payload_json = _payload_json(notification)

    for rec in recipients:
        subs = PushSubscription.objects.filter(user=rec.user, is_active=True)
        for sub in subs:
            delivery, _ = NotificationDelivery.objects.get_or_create(
                recipient=rec, subscription=sub, defaults={"status": DeliveryStatus.PENDING}
            )
            if delivery.status in (DeliveryStatus.SENT, DeliveryStatus.EXPIRED):
                continue
            _attempt_delivery(delivery, payload_json)

    notification.status = NotificationStatus.SENT
    notification.sent_at = timezone.now()
    notification.save(update_fields=["status", "sent_at", "updated_at"])
    return recompute_counts(notification)


def retry_pending_deliveries(limit: int = 500) -> int:
    """Re-attempt failed deliveries whose backoff has elapsed. Returns count."""
    now = timezone.now()
    due = (
        NotificationDelivery.objects.filter(
            status=DeliveryStatus.FAILED,
            attempts__lt=MAX_RETRIES,
        )
        .filter(Q(next_retry_at__isnull=True) | Q(next_retry_at__lte=now))
        .select_related("recipient__notification", "subscription")[:limit]
    )
    count = 0
    touched = set()
    for delivery in due:
        payload_json = _payload_json(delivery.recipient.notification)
        _attempt_delivery(delivery, payload_json)
        touched.add(delivery.recipient.notification_id)
        count += 1
    for nid in touched:
        try:
            recompute_counts(Notification.objects.get(id=nid))
        except Notification.DoesNotExist:  # pragma: no cover
            pass
    return count


def recompute_counts(notification: Notification) -> dict:
    """Recompute denormalised counters from the source-of-truth rows."""
    recs = NotificationRecipient.objects.filter(notification=notification)
    notification.recipients_count = recs.count()
    notification.delivered_count = recs.filter(delivered=True).count()
    notification.read_count = recs.filter(is_read=True).count()
    notification.failed_count = NotificationDelivery.objects.filter(
        recipient__notification=notification, status=DeliveryStatus.FAILED, attempts__gte=MAX_RETRIES
    ).count()
    notification.save(
        update_fields=["recipients_count", "delivered_count", "read_count", "failed_count", "updated_at"]
    )
    return {
        "recipients": notification.recipients_count,
        "delivered": notification.delivered_count,
        "read": notification.read_count,
        "failed": notification.failed_count,
    }


def _payload_json(notification: Notification) -> str:
    import json

    return json.dumps(notification.to_push_payload())


# --------------------------------------------------------------------------- #
# High-level orchestration
# --------------------------------------------------------------------------- #
@transaction.atomic
def create_notification(
    *,
    hostel,
    title: str,
    body: str = "",
    category: str = "GENERAL",
    priority: str = "NORMAL",
    url: str = "/dashboard",
    icon: str = "",
    tag: str = "",
    data: dict | None = None,
    audience: str = AudienceType.ALL,
    target_roles=None,
    user_ids=None,
    created_by=None,
    scheduled_at=None,
    send: bool = True,
    async_dispatch: bool = True,
) -> Notification:
    """Create a notification, resolve recipients, then schedule or dispatch it.

    This is the single entry point used by the API, admin and the ``events``
    helpers. Recipients are materialised immediately (even when scheduled) so the
    audience is captured at creation time.
    """
    is_scheduled = bool(scheduled_at and scheduled_at > timezone.now())
    notification = Notification.objects.create(
        hostel=hostel,
        title=title,
        body=body,
        category=category,
        priority=priority,
        url=url or "/dashboard",
        icon=icon,
        tag=tag,
        data=data or {},
        audience=audience,
        target_roles=list(target_roles or []),
        created_by=created_by,
        scheduled_at=scheduled_at,
        status=NotificationStatus.SCHEDULED if is_scheduled else NotificationStatus.DRAFT,
    )
    build_recipients(notification, explicit_user_ids=user_ids)

    if is_scheduled or not send:
        return notification

    # Dispatch now. Use Celery when a real broker is in play so the request
    # returns fast; when tasks run eagerly (tests/no broker) dispatch inline so
    # the result is observable synchronously (on_commit hooks don't fire inside
    # a test's rolled-back transaction).
    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    if async_dispatch and not eager:
        from .tasks import dispatch_notification_task

        # Commit first so the worker can read the rows.
        transaction.on_commit(
            lambda: dispatch_notification_task.delay(str(notification.id), user_ids=list(user_ids or []))
        )
    else:
        dispatch(notification, explicit_user_ids=user_ids)
    return notification
