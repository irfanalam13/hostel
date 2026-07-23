"""Tests for the push-notification system.

Covers the API contract (subscribe/unsubscribe, inbox, read state, staff send),
tenant isolation, scheduling, the event helpers, and that dispatch is robust
when VAPID isn't configured (delivery fails gracefully, never raises).
"""
import datetime as dt

import pytest
from django.utils import timezone

from apps.notifications import events
from apps.notifications.models import (
    AudienceType,
    Notification,
    NotificationCategory,
    NotificationRecipient,
    NotificationStatus,
    PushSubscription,
)
from apps.notifications.services import create_notification
from apps.notifications.tasks import send_scheduled_notifications

pytestmark = pytest.mark.django_db

SUBSCRIBE = "/api/push/subscribe/"
UNSUBSCRIBE = "/api/push/unsubscribe/"
INBOX = "/api/notifications/"
SEND = "/api/notifications/send/"

SUB_PAYLOAD = {
    "subscription": {
        "endpoint": "https://push.example.com/sub/abc123",
        "keys": {"p256dh": "BPk_key_value", "auth": "auth_value"},
    },
    "user_agent": "pytest-agent",
}


@pytest.fixture
def staff_client(auth_client, warden, hostel):
    return auth_client(warden, hostel)


# --------------------------------------------------------------------------- #
# Push subscription endpoints
# --------------------------------------------------------------------------- #
def test_subscribe_creates_subscription(staff_client, warden):
    resp = staff_client.post(SUBSCRIBE, SUB_PAYLOAD, format="json")
    assert resp.status_code == 201
    sub = PushSubscription.objects.get(user=warden)
    assert sub.endpoint == SUB_PAYLOAD["subscription"]["endpoint"]
    assert sub.p256dh == "BPk_key_value"
    assert sub.is_active


def test_subscribe_is_idempotent(staff_client, warden):
    staff_client.post(SUBSCRIBE, SUB_PAYLOAD, format="json")
    resp = staff_client.post(SUBSCRIBE, SUB_PAYLOAD, format="json")
    assert resp.status_code == 200  # update, not create
    assert PushSubscription.objects.filter(user=warden).count() == 1


def test_subscribe_requires_auth(api):
    assert api.post(SUBSCRIBE, SUB_PAYLOAD, format="json").status_code in (401, 403)


def test_unsubscribe_removes_subscription(staff_client, warden):
    staff_client.post(SUBSCRIBE, SUB_PAYLOAD, format="json")
    resp = staff_client.post(
        UNSUBSCRIBE, {"endpoint": SUB_PAYLOAD["subscription"]["endpoint"]}, format="json"
    )
    assert resp.status_code == 200
    assert resp.data["removed"] is True
    assert not PushSubscription.objects.filter(user=warden).exists()


def test_invalid_subscription_rejected(staff_client):
    bad = {"subscription": {"endpoint": "", "keys": {}}}
    assert staff_client.post(SUBSCRIBE, bad, format="json").status_code == 400


# --------------------------------------------------------------------------- #
# Staff send + inbox + read state
# --------------------------------------------------------------------------- #
def test_staff_can_send_to_all(staff_client, make_user, hostel):
    make_user(role="RESIDENT", hostel=hostel)
    make_user(role="MANAGER", hostel=hostel)
    resp = staff_client.post(
        SEND,
        {"title": "Water cut", "body": "No water 2-4pm", "audience": "ALL", "category": "STAFF_NOTICE"},
        format="json",
    )
    assert resp.status_code == 201
    n = Notification.objects.get(id=resp.data["id"])
    assert n.status == NotificationStatus.SENT
    # warden (sender) + resident + manager = 3 hostel members
    assert n.recipients_count == 3


def test_non_staff_cannot_send(auth_client, resident_user, hostel):
    client = auth_client(resident_user, hostel)
    resp = client.post(SEND, {"title": "x", "audience": "ALL"}, format="json")
    assert resp.status_code == 403


def test_role_targeting(staff_client, make_user, hostel):
    make_user(role="RESIDENT", hostel=hostel)
    accountant = make_user(role="ACCOUNTANT", hostel=hostel)
    resp = staff_client.post(
        SEND,
        {"title": "Books", "audience": "ROLE", "target_roles": ["ACCOUNTANT"]},
        format="json",
    )
    assert resp.status_code == 201
    n = Notification.objects.get(id=resp.data["id"])
    assert n.recipients_count == 1
    assert NotificationRecipient.objects.filter(notification=n, user=accountant).exists()


def test_role_targeting_requires_roles(staff_client):
    resp = staff_client.post(SEND, {"title": "x", "audience": "ROLE"}, format="json")
    assert resp.status_code == 400


def test_inbox_and_read_flow(staff_client, auth_client, make_user, hostel):
    resident = make_user(role="RESIDENT", hostel=hostel)
    staff_client.post(SEND, {"title": "Hi", "audience": "ALL"}, format="json")

    rc = auth_client(resident, hostel)
    inbox = rc.get(INBOX)
    assert inbox.status_code == 200
    items = inbox.data["results"] if isinstance(inbox.data, dict) else inbox.data
    assert len(items) == 1
    assert items[0]["is_read"] is False

    assert rc.get(INBOX + "unread_count/").data["unread"] == 1

    rec_id = items[0]["recipient_id"]
    assert rc.post(f"{INBOX}{rec_id}/read/").status_code == 200
    assert rc.get(INBOX + "unread_count/").data["unread"] == 0


def test_read_all(staff_client, auth_client, make_user, hostel):
    resident = make_user(role="RESIDENT", hostel=hostel)
    staff_client.post(SEND, {"title": "A", "audience": "ALL"}, format="json")
    staff_client.post(SEND, {"title": "B", "audience": "ALL"}, format="json")
    rc = auth_client(resident, hostel)
    assert rc.get(INBOX + "unread_count/").data["unread"] == 2
    assert rc.post(INBOX + "read_all/").data["marked_read"] == 2
    assert rc.get(INBOX + "unread_count/").data["unread"] == 0


# --------------------------------------------------------------------------- #
# Tenant isolation
# --------------------------------------------------------------------------- #
def test_tenant_isolation(staff_client, auth_client, make_user, hostel, other_hostel):
    # A user only in other_hostel must never receive hostel's notification.
    outsider = make_user(role="RESIDENT", hostel=other_hostel)
    staff_client.post(SEND, {"title": "Secret", "audience": "ALL"}, format="json")

    rc = auth_client(outsider, other_hostel)
    inbox = rc.get(INBOX)
    items = inbox.data["results"] if isinstance(inbox.data, dict) else inbox.data
    assert items == []


# --------------------------------------------------------------------------- #
# Scheduling
# --------------------------------------------------------------------------- #
def test_scheduled_notification_not_sent_until_due(hostel, warden):
    future = timezone.now() + dt.timedelta(hours=2)
    n = create_notification(
        hostel=hostel, title="Later", audience=AudienceType.ALL,
        created_by=warden, scheduled_at=future,
    )
    assert n.status == NotificationStatus.SCHEDULED
    assert send_scheduled_notifications() == 0  # nothing due yet

    n.scheduled_at = timezone.now() - dt.timedelta(minutes=1)
    n.save(update_fields=["scheduled_at"])
    assert send_scheduled_notifications() == 1
    n.refresh_from_db()
    assert n.status == NotificationStatus.SENT


# --------------------------------------------------------------------------- #
# Event helpers
# --------------------------------------------------------------------------- #
def test_admission_approved_event(hostel, resident_user):
    n = events.admission_approved(hostel, resident_user, "Asha")
    assert n is not None
    assert n.category == NotificationCategory.ADMISSION_APPROVED
    assert n.audience == AudienceType.USER
    assert NotificationRecipient.objects.filter(notification=n, user=resident_user).exists()


def test_emergency_event_targets_all(hostel, warden, make_user):
    make_user(role="RESIDENT", hostel=hostel)
    n = events.emergency_announcement(hostel, "Evacuate now", created_by=warden)
    assert n.priority == "URGENT"
    assert n.require_interaction is True
    assert n.recipients_count == 2


# --------------------------------------------------------------------------- #
# Dispatch is robust without VAPID configured
# --------------------------------------------------------------------------- #
def test_dispatch_without_vapid_does_not_crash(hostel, warden):
    PushSubscription.objects.create(
        user=warden, hostel=hostel, endpoint="https://push.example/x",
        p256dh="k", auth="a", is_active=True,
    )
    n = create_notification(
        hostel=hostel, title="Hi", audience=AudienceType.USER,
        user_ids=[warden.id], created_by=warden, async_dispatch=False,
    )
    n.refresh_from_db()
    assert n.status == NotificationStatus.SENT
    # No VAPID in test settings → nothing actually delivered, but no exception.
    assert n.delivered_count == 0
