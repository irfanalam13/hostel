"""Domain event helpers — call these from other apps to fire a notification.

Each helper picks the right category/priority/audience/deep-link so callers don't
have to. Example::

    from apps.notifications import events
    events.admission_approved(hostel, student_user, "Asha Gurung")

All helpers are safe to call inside a request: dispatch is handed to Celery (or
runs eagerly in tests). They return the created ``Notification`` (or ``None`` if
no user was supplied for a user-targeted event).
"""
from __future__ import annotations

from .models import AudienceType, NotificationCategory, NotificationPriority
from .services import create_notification

STAFF_ROLES = ["ADMIN", "OWNER", "MANAGER", "WARDEN", "STAFF"]
MANAGER_ROLES = ["ADMIN", "OWNER", "MANAGER"]


def _user_id(user):
    return getattr(user, "id", user)


def admission_approved(hostel, student_user, student_name: str, *, created_by=None):
    if student_user is None:
        return None
    return create_notification(
        hostel=hostel,
        category=NotificationCategory.ADMISSION_APPROVED,
        title="Admission approved 🎉",
        body=f"Welcome {student_name}! Your hostel admission has been approved.",
        url="/dashboard",
        audience=AudienceType.USER,
        user_ids=[_user_id(student_user)],
        created_by=created_by,
    )


def fee_due_reminder(hostel, user, amount, due_date, *, created_by=None):
    return create_notification(
        hostel=hostel,
        category=NotificationCategory.FEE_DUE,
        title="Fee due reminder",
        body=f"Your fee of Rs. {amount} is due on {due_date}.",
        url="/fees",
        audience=AudienceType.USER,
        user_ids=[_user_id(user)],
        data={"amount": str(amount), "due_date": str(due_date)},
        created_by=created_by,
    )


def rent_overdue(hostel, user, amount, days_overdue, *, created_by=None):
    return create_notification(
        hostel=hostel,
        category=NotificationCategory.RENT_OVERDUE,
        priority=NotificationPriority.HIGH,
        title="Rent overdue",
        body=f"Your rent of Rs. {amount} is {days_overdue} day(s) overdue. Please pay to avoid penalties.",
        url="/payments",
        audience=AudienceType.USER,
        user_ids=[_user_id(user)],
        data={"amount": str(amount), "days_overdue": days_overdue},
        created_by=created_by,
    )


def visitor_approval(hostel, host_user, visitor_name: str, *, created_by=None):
    return create_notification(
        hostel=hostel,
        category=NotificationCategory.VISITOR_APPROVAL,
        priority=NotificationPriority.HIGH,
        title="Visitor awaiting approval",
        body=f"{visitor_name} is at the gate and needs your approval.",
        url="/visitors",
        audience=AudienceType.USER,
        user_ids=[_user_id(host_user)],
        created_by=created_by,
    )


def room_changed(hostel, user, old_room: str, new_room: str, *, created_by=None):
    return create_notification(
        hostel=hostel,
        category=NotificationCategory.ROOM_CHANGED,
        title="Room changed",
        body=f"You've been moved from room {old_room} to room {new_room}.",
        url="/rooms",
        audience=AudienceType.USER,
        user_ids=[_user_id(user)],
        data={"old_room": old_room, "new_room": new_room},
        created_by=created_by,
    )


def maintenance_completed(hostel, user, item: str, *, created_by=None):
    return create_notification(
        hostel=hostel,
        category=NotificationCategory.MAINTENANCE_COMPLETED,
        title="Maintenance completed",
        body=f"The maintenance request for “{item}” has been completed.",
        url="/complaints",
        audience=AudienceType.USER,
        user_ids=[_user_id(user)],
        created_by=created_by,
    )


def complaint_resolved(hostel, user, complaint_title: str, *, created_by=None):
    return create_notification(
        hostel=hostel,
        category=NotificationCategory.COMPLAINT_RESOLVED,
        title="Complaint resolved",
        body=f"Your complaint “{complaint_title}” has been marked resolved.",
        url="/complaints",
        audience=AudienceType.USER,
        user_ids=[_user_id(user)],
        created_by=created_by,
    )


def emergency_announcement(hostel, message: str, *, title: str = "Emergency announcement", created_by=None):
    return create_notification(
        hostel=hostel,
        category=NotificationCategory.EMERGENCY,
        priority=NotificationPriority.URGENT,
        title=title,
        body=message,
        url="/notices",
        audience=AudienceType.ALL,
        created_by=created_by,
    )


def staff_notice(hostel, title: str, body: str, *, created_by=None):
    return create_notification(
        hostel=hostel,
        category=NotificationCategory.STAFF_NOTICE,
        title=title,
        body=body,
        url="/notices",
        audience=AudienceType.ROLE,
        target_roles=STAFF_ROLES,
        created_by=created_by,
    )


def inventory_alert(hostel, item: str, *, detail: str = "", created_by=None):
    return create_notification(
        hostel=hostel,
        category=NotificationCategory.INVENTORY_ALERT,
        priority=NotificationPriority.HIGH,
        title="Inventory alert",
        body=detail or f"Low stock: {item}. Please restock.",
        url="/operations",
        audience=AudienceType.ROLE,
        target_roles=MANAGER_ROLES,
        data={"item": item},
        created_by=created_by,
    )
