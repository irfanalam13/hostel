"""Email backends that don't depend on outbound SMTP.

Render's free/starter tiers (like many PaaS) filter outbound SMTP — a TCP
connect to Brevo on 25/465/587 just times out, and even the "alternate"
port 2525 is not guaranteed. Brevo also exposes a **transactional HTTP API**
(``POST https://api.brevo.com/v3/smtp/email``) over plain HTTPS/443, which no
PaaS blocks. This backend speaks that API while presenting the ordinary Django
email interface, so every existing ``send_mail`` / ``EmailMessage`` /
``EmailMultiAlternatives`` call keeps working unchanged.

Switch to it with two env vars — no call-site changes::

    EMAIL_BACKEND=apps.common.email_backends.BrevoAPIEmailBackend
    BREVO_API_KEY=xkeysib-...        # Brevo → SMTP & API → API Keys

The ``from`` address/domain must still be a *verified sender* in Brevo, exactly
as with SMTP.
"""
from __future__ import annotations

import logging
from email.utils import getaddresses, parseaddr

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger("apps.common.email")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _split_addr(address):
    """"Name <a@b.com>" -> {"name": "Name", "email": "a@b.com"} (name omitted if empty)."""
    name, email = parseaddr(address)
    entry = {"email": email}
    if name:
        entry["name"] = name
    return entry


def _recipients(addresses):
    return [_split_addr(email) for _, email in getaddresses(addresses)] if addresses else []


class BrevoAPIEmailBackend(BaseEmailBackend):
    """Deliver Django email through Brevo's transactional HTTP API (HTTPS/443).

    Honours ``fail_silently``: on error it either swallows the exception and
    returns 0, or re-raises so a Celery task's retry logic can act on it.
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = getattr(settings, "BREVO_API_KEY", "") or ""
        self.api_url = getattr(settings, "BREVO_API_URL", BREVO_API_URL)
        self.timeout = int(getattr(settings, "EMAIL_TIMEOUT", 10) or 10)
        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "api-key": self.api_key,
                "accept": "application/json",
                "content-type": "application/json",
            })
        return self._session

    def send_messages(self, email_messages):
        email_messages = list(email_messages or [])
        if not email_messages:
            return 0
        if not self.api_key:
            if not self.fail_silently:
                raise ValueError(
                    "BREVO_API_KEY is not set; cannot send via BrevoAPIEmailBackend."
                )
            logger.error("BREVO_API_KEY is not set; dropping %d message(s).",
                         len(email_messages))
            return 0

        sent = 0
        for message in email_messages:
            if self._send(message):
                sent += 1
        return sent

    def _payload(self, message):
        from_email = message.from_email or settings.DEFAULT_FROM_EMAIL
        payload = {
            "sender": _split_addr(from_email),
            "to": _recipients(message.to),
            "subject": message.subject,
        }
        if message.cc:
            payload["cc"] = _recipients(message.cc)
        if message.bcc:
            payload["bcc"] = _recipients(message.bcc)
        reply_to = getattr(message, "reply_to", None)
        if reply_to:
            payload["replyTo"] = _split_addr(reply_to[0])

        # Body: plain text lives in .body; an HTML alternative (from
        # EmailMultiAlternatives) or content_subtype == "html" becomes htmlContent.
        body = message.body or ""
        if getattr(message, "content_subtype", "plain") == "html":
            payload["htmlContent"] = body
        else:
            payload["textContent"] = body
        for content, mimetype in getattr(message, "alternatives", []) or []:
            if mimetype == "text/html":
                payload["htmlContent"] = content
        return payload

    def _send(self, message):
        try:
            response = self.session.post(
                self.api_url, json=self._payload(message), timeout=self.timeout
            )
            if response.status_code >= 400:
                # Brevo returns a JSON body with a "message"/"code" on error.
                raise requests.HTTPError(
                    f"Brevo API {response.status_code}: {response.text[:500]}"
                )
        except Exception as exc:  # noqa: BLE001 - normalise to Django's contract
            logger.warning("Brevo API send failed: %s", exc)
            if not self.fail_silently:
                raise
            return False
        return True
