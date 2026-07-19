"""Send a single test email to verify SMTP / Brevo delivery.

Unlike the password-reset and hostel-id flows (which use ``fail_silently=True``
so they never break the request), this command sends with ``fail_silently=False``
and prints the active configuration, so any SMTP/auth/sender error is surfaced.

Usage (inside the web container)::

    python manage.py send_test_email you@example.com

A common cause of "no email arrives" with Brevo is an unverified sender: the
``DEFAULT_FROM_EMAIL`` address/domain must be verified in the Brevo dashboard.
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test email to verify SMTP delivery (errors are surfaced, not swallowed)."

    def add_arguments(self, parser):
        parser.add_argument("recipient", help="Destination email address.")

    def handle(self, *args, **options):
        recipient = options["recipient"]

        self.stdout.write("Email configuration:")
        self.stdout.write(f"  EMAIL_BACKEND      = {settings.EMAIL_BACKEND}")
        self.stdout.write(f"  BREVO_API_KEY set  = {bool(getattr(settings, 'BREVO_API_KEY', ''))}")
        self.stdout.write(f"  BREVO_API_URL      = {getattr(settings, 'BREVO_API_URL', '')}")
        self.stdout.write(f"  DEFAULT_FROM_EMAIL = {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"Sending test email to {recipient} ...")

        try:
            sent = send_mail(
                subject="Hostel SMTP delivery test",
                message=(
                    "This is a test email from your Hostel deployment.\n\n"
                    "If you received this, SMTP delivery is working."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception as exc:  # surface the real SMTP error
            raise CommandError(f"send_mail failed: {exc!r}") from exc

        if sent:
            self.stdout.write(self.style.SUCCESS(
                f"send_mail accepted the message ({sent} sent). "
                f"Check the inbox AND spam folder for {recipient}."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "send_mail returned 0 — the backend reported the message was not sent."
            ))
