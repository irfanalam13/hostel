"""apps.common.emails: the shared branded welcome-email helper.

Covers the two branches every caller (signup, staff invite, team invite,
student admission) depends on: a no-op for an empty recipient, and the
fail_silently contract on a render/send error (best-effort invites swallow it,
Celery-task callers need it to propagate so they can retry).
"""
from unittest.mock import patch

import pytest
from django.core import mail

from apps.common.emails import send_account_welcome

pytestmark = pytest.mark.django_db


def test_send_account_welcome_noop_without_recipient():
    assert send_account_welcome(to="", subject="Welcome") is False
    assert len(mail.outbox) == 0


def test_send_account_welcome_sends_via_locmem():
    sent = send_account_welcome(
        to="new-owner@example.com",
        subject="Welcome aboard",
        context={"recipient_name": "Asha", "workspace_name": "Everest Hostel"},
    )
    assert sent is True
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["new-owner@example.com"]


def test_send_account_welcome_fail_silently_swallows_error():
    with patch("apps.common.emails.render_to_string", side_effect=RuntimeError("boom")):
        sent = send_account_welcome(to="a@example.com", subject="x", fail_silently=True)
    assert sent is False
    assert len(mail.outbox) == 0


def test_send_account_welcome_reraises_when_not_fail_silently():
    with patch("apps.common.emails.render_to_string", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            send_account_welcome(to="a@example.com", subject="x", fail_silently=False)
