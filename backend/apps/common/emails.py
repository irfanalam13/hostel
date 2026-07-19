"""Shared branded transactional-email helpers.

Every onboarding / welcome email (owner signup, staff invite, team-member
invite, student admission) renders the same ``emails/account_welcome`` template
pair (HTML + plaintext) so the four surfaces stay visually and structurally
consistent — only the per-recipient context differs. The Brevo API backend maps
the attached HTML alternative to ``htmlContent`` automatically
(see ``apps.common.email_backends``).
"""
from __future__ import annotations

import logging
from typing import Iterable

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger("apps.common.emails")

# Context keys the template understands. Every one is optional; the template
# guards each, so callers only pass what they have.
_WELCOME_DEFAULTS = {
    "sender_name": "",
    "logo": "",
    "recipient_name": "",
    "workspace_name": "",
    "workspace_url": "",
    "hostel_code": "",
    "login_identity": "",
    "role_label": "",
    "credential_note": "",
    "first_login_note": "",
    "support_email": "",
    "footer_text": "",
}


def welcome_context_from_branding(brand: dict) -> dict:
    """Seed a welcome-email context from ``apps.tenants.branding.email_branding``.

    Maps the tenant branding dict onto the template's field names (workspace URL,
    sender name, logo, support address, footer). Callers overlay the
    recipient-specific keys (recipient_name, login_identity, role_label, …).
    """
    return {
        "sender_name": brand.get("sender_name", ""),
        "logo": brand.get("logo", ""),
        "workspace_url": brand.get("site_url", ""),
        "support_email": brand.get("contact_email", ""),
        "footer_text": brand.get("footer_text", ""),
    }


def send_account_welcome(
    *,
    to: str | Iterable[str],
    subject: str,
    context: dict | None = None,
    from_email: str | None = None,
    fail_silently: bool = False,
) -> bool:
    """Render and send the branded account-welcome email.

    Returns ``True`` when a message was sent. With ``fail_silently=True`` any
    render/send error is swallowed (best-effort invites); otherwise it
    propagates so a Celery task can retry.
    """
    if not to:
        return False

    ctx = {**_WELCOME_DEFAULTS, **(context or {})}
    recipients = [to] if isinstance(to, str) else list(to)
    try:
        html_body = render_to_string("emails/account_welcome.html", ctx)
        text_body = render_to_string("emails/account_welcome.txt", ctx)
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=fail_silently)
        return True
    except Exception:
        logger.warning("account-welcome email to %s failed", recipients, exc_info=True)
        if not fail_silently:
            raise
        return False
