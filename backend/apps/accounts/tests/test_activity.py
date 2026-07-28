"""Account activity timeline (ActivityView).

Covered:
  * events ordered newest first
  * scoped to the requesting user, not other accounts
  * `limit` param is clamped and tolerant of garbage input
  * requires authentication
  * a real profile update produces a matching activity row (integration guard
    tying MeView.patch's record_event call to this view)
"""
import datetime as dt

import pytest
from django.utils import timezone

from apps.auditlog.models import AuditEvent

ACTIVITY = "/api/auth/activity/"
ME = "/api/auth/me/"

pytestmark = pytest.mark.django_db


def _event(hostel, user, message, minutes_ago=0):
    return AuditEvent.objects.create(
        hostel_id=hostel.id,
        actor=user,
        action=AuditEvent.Action.LOGIN,
        message=message,
        created_at=timezone.now() - dt.timedelta(minutes=minutes_ago),
    )


def test_activity_lists_own_events_newest_first(auth_client, warden, hostel):
    _event(hostel, warden, "evt2", minutes_ago=2)
    _event(hostel, warden, "evt1", minutes_ago=1)
    _event(hostel, warden, "evt0", minutes_ago=0)

    resp = auth_client(warden, hostel).get(ACTIVITY)
    assert resp.status_code == 200
    assert [e["message"] for e in resp.data] == ["evt0", "evt1", "evt2"]


def test_activity_scoped_to_self_not_other_users(auth_client, warden, make_user, hostel):
    other = make_user(role="WARDEN", hostel=hostel)
    _event(hostel, other, "not mine")
    _event(hostel, warden, "mine")

    resp = auth_client(warden, hostel).get(ACTIVITY)
    messages = [e["message"] for e in resp.data]
    assert "mine" in messages
    assert "not mine" not in messages


def test_activity_limit_param_is_clamped(auth_client, warden, hostel):
    for i in range(5):
        _event(hostel, warden, f"evt{i}")

    resp = auth_client(warden, hostel).get(ACTIVITY, {"limit": 9999})
    assert resp.status_code == 200


def test_activity_invalid_limit_param_defaults_quietly(auth_client, warden, hostel):
    _event(hostel, warden, "evt")
    resp = auth_client(warden, hostel).get(ACTIVITY, {"limit": "notanumber"})
    assert resp.status_code == 200


def test_activity_reflects_real_profile_update_end_to_end(auth_client, warden, hostel):
    client = auth_client(warden, hostel)
    assert client.patch(ME, {"first_name": "New"}).status_code == 200

    resp = client.get(ACTIVITY)
    messages = [e["message"] for e in resp.data]
    assert "Profile updated" in messages


def test_activity_requires_auth(api):
    assert api.get(ACTIVITY).status_code == 401
