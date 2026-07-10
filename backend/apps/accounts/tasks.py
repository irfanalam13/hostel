"""Celery tasks for the accounts app.

Auth emails (signup OTP, etc.) are sent off the request/response cycle so a slow
or unreachable SMTP host can never block, hang, or drop the HTTP request. The
view enqueues the task and returns immediately; delivery (with retries) happens
in the worker.
"""
import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger("apps.accounts")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_signup_otp_email(self, email, otp_code):
    """Email a signup verification OTP. Retries on transient SMTP failures."""
    try:
        send_mail(
            subject="Verify your email to create your Hostel account",
            message=(
                "Welcome to Hostel!\n\n"
                f"Your email verification code (OTP) is: {otp_code}\n\n"
                "Enter this code on the signup page to create your account. "
                "It is valid for 15 minutes.\n\n"
                "If you did not request this, you can safely ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as exc:  # noqa: BLE001 - retry any transient delivery error
        logger.warning("signup OTP email to %s failed (attempt %s): %s",
                       email, self.request.retries + 1, exc)
        raise self.retry(exc=exc)

    logger.info("signup OTP email sent to %s", email)
    return {"sent": True, "email": email}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_hostel_id_email(self, email, username, hostel_name, hostel_code):
    """Email the newly created Hostel ID once an account is verified & created.

    Sent off the request cycle (like the signup OTP) so SMTP latency never blocks
    the signup response. Retries on transient SMTP failures.
    """
    try:
        send_mail(
            subject="Your Hostel ID — account created successfully",
            message=(
                f"Hello {username},\n\n"
                "Your Hostel account has been created successfully.\n\n"
                f"Hostel name: {hostel_name}\n"
                f"Your Hostel ID is: {hostel_code}\n\n"
                "Keep this Hostel ID safe — you will need it (along with your "
                "username and password) every time you log in.\n\n"
                "If you did not create this account, please contact support."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as exc:  # noqa: BLE001 - retry any transient delivery error
        logger.warning("Hostel ID email to %s failed (attempt %s): %s",
                       email, self.request.retries + 1, exc)
        raise self.retry(exc=exc)

    logger.info("Hostel ID email sent to %s (hostel %s)", email, hostel_code)
    return {"sent": True, "email": email, "hostel_code": hostel_code}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_otp_email(self, email, otp_code):
    """Email a password-reset OTP. Retries on transient SMTP failures."""
    try:
        send_mail(
            subject="Reset your Hostel account password",
            message=(
                "We received a request to reset your password.\n\n"
                f"Your One-Time Password (OTP) is: {otp_code}\n\n"
                "This OTP is valid for 15 minutes. "
                "If you did not request this, you can safely ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as exc:  # noqa: BLE001 - retry any transient delivery error
        logger.warning("password reset OTP email to %s failed (attempt %s): %s",
                       email, self.request.retries + 1, exc)
        raise self.retry(exc=exc)

    logger.info("password reset OTP email sent to %s", email)
    return {"sent": True, "email": email}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_hostel_id_list_email(self, email, username, hostels_info):
    """Email the list of Hostel IDs linked to an account (forgot-ID flow)."""
    try:
        send_mail(
            subject="Your Hostel ID Details",
            message=(
                f"Hello {username},\n\n"
                "You requested your Hostel ID(s) associated with this account.\n\n"
                "Here is your Hostel ID list:\n"
                + "\n".join(hostels_info) + "\n\n"
                "You can use these Hostel IDs to log in or manage your hostels.\n\n"
                "If you did not request this, you can safely ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as exc:  # noqa: BLE001 - retry any transient delivery error
        logger.warning("Hostel ID list email to %s failed (attempt %s): %s",
                       email, self.request.retries + 1, exc)
        raise self.retry(exc=exc)

    logger.info("Hostel ID list email sent to %s", email)
    return {"sent": True, "email": email}
