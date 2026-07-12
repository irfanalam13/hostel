"""Tenant branding context (Prompt 05) — one helper every outbound surface
uses so branding propagates consistently.

* ``email_branding(hostel)``   → sender display name, from address, logo,
                                 footer for tenant emails
* ``pdf_branding(hostel)``     → logo/colors/business info/header/footer for
                                 WeasyPrint exports (receipts, reports, forms)
* ``white_label(hostel)``      → the effective white-label config (with the
                                 hostel name as the natural fallback)

All values come from the workspace-settings namespaces (branding, business,
white_label) plus the primary custom domain, so a fully white-labelled tenant
never surfaces the platform's name or domain.
"""
from django.conf import settings as dj_settings

from .workspace_settings import get_workspace_settings


def white_label(hostel) -> dict:
    config = get_workspace_settings(hostel, "white_label")
    platform_name = config.get("platform_name") or hostel.name
    return {
        **config,
        "platform_name": platform_name,
        "browser_title": config.get("browser_title") or platform_name,
    }


def public_url(hostel) -> str:
    from apps.domains.services import public_url_for

    return public_url_for(hostel)


def email_branding(hostel) -> dict:
    """Branding for tenant-originated emails. The From *address* stays the
    platform's authenticated sender (SPF/DKIM); the display name, logo and
    footer are the tenant's. Custom SMTP per tenant is future-ready — swap
    ``from_email`` here once per-workspace SMTP config ships."""
    wl = white_label(hostel)
    branding = get_workspace_settings(hostel, "branding")
    profile = get_workspace_settings(hostel, "profile")
    sender_name = wl.get("email_sender_name") or wl["platform_name"]
    return {
        "sender_name": sender_name,
        "from_email": f"{sender_name} <{dj_settings.DEFAULT_FROM_EMAIL}>",
        "logo": branding.get("logo") or "",
        "site_url": public_url(hostel),
        "contact_email": profile.get("contact_email") or "",
        "contact_phone": profile.get("contact_phone") or "",
        "footer_text": wl.get("footer_text")
        or f"{hostel.name} · {public_url(hostel)}",
    }


def pdf_branding(hostel) -> dict:
    """Branding context for PDF exports (receipts, fee reports, admission
    forms). Exports render this dict into their header/footer templates."""
    from apps.website.models import Website

    branding = get_workspace_settings(hostel, "branding")
    business = get_workspace_settings(hostel, "business")
    wl = white_label(hostel)

    theme = {}
    website = Website.objects.filter(hostel=hostel).only("theme").first()
    if website:
        theme = website.effective_theme()

    return {
        "logo": branding.get("logo") or "",
        "name": wl["platform_name"],
        "primary_color": theme.get("primary_color", "#2563eb"),
        "secondary_color": theme.get("secondary_color", "#0f172a"),
        "business": {
            "legal_name": business.get("business_name") or hostel.name,
            "pan_vat": business.get("pan_vat_number") or "",
            "registration": business.get("registration_number") or "",
            "address": ", ".join(filter(None, [
                business.get("address"), business.get("city"),
                business.get("district"), business.get("province"),
                business.get("country"),
            ])),
        },
        "header": wl["platform_name"],
        "footer": wl.get("footer_text") or f"{hostel.name} · {public_url(hostel)}",
    }
