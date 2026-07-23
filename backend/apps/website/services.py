"""Website Builder domain services: scaffolding, publishing, versioning."""
import logging

from django.db import transaction
from django.utils import timezone

from .models import Website, WebsiteInquiry, WebsiteSection, WebsiteVersion
from .sections import DEFAULT_SECTION_ORDER, SECTION_TYPES, default_content_for

logger = logging.getLogger(__name__)


def _audit(hostel, actor, message, meta=None):
    try:
        from apps.auditlog.models import AuditEvent

        AuditEvent.objects.create(
            hostel_id=hostel.pk,
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            action=AuditEvent.Action.UPDATE,
            entity_type="website",
            entity_id=str(hostel.pk),
            message=message,
            meta=meta or {},
        )
    except Exception:
        logger.exception("website audit write failed (hostel=%s)", hostel.pk)


@transaction.atomic
def get_or_scaffold_website(hostel) -> Website:
    """The workspace's website, creating a sensible default on first access.

    Every hostel "automatically receives a professional public website": the
    scaffold seeds the standard sections with the hostel's name woven in and
    publishes it as version 1, so the public URL works from day one.
    """
    website = Website.objects.filter(hostel=hostel).first()
    if website:
        return website

    website = Website.objects.create(
        hostel=hostel,
        seo={"meta_title": hostel.name,
             "meta_description": f"{hostel.name} — rooms, facilities, pricing and contact."},
        footer={"copyright": f"© {timezone.localdate().year} {hostel.name}"},
    )
    for index, section_type in enumerate(DEFAULT_SECTION_ORDER):
        content = default_content_for(section_type)
        if section_type == "hero":
            content["headline"] = hostel.name
        if section_type == "contact":
            content["phone"] = hostel.phone or ""
            content["address"] = hostel.address or ""
        WebsiteSection.objects.create(
            website=website, type=section_type, order=index, content=content
        )

    # Auto-publish the scaffold so the public site is live immediately.
    publish_website(website, actor=None, note="Initial website")
    return website


def build_snapshot(website: Website) -> dict:
    """Serialize the entire draft into one JSON document (the version unit)."""
    return {
        "theme": website.effective_theme(),
        "seo": website.effective_seo(),
        "branding": website.effective_branding(),
        "navigation": website.effective_navigation(),
        "footer": website.effective_footer(),
        "social": website.effective_social(),
        "sections": [
            {
                "id": str(s.id),
                "type": s.type,
                "order": s.order,
                "is_visible": s.is_visible,
                "content": s.content,
            }
            for s in website.sections.all().order_by("order", "created_at")
        ],
    }


@transaction.atomic
def publish_website(website: Website, actor=None, note: str = "") -> WebsiteVersion:
    """Snapshot the draft, store it as the next version, and make it live."""
    snapshot = build_snapshot(website)
    number = website.published_version + 1
    version = WebsiteVersion.objects.create(
        website=website, number=number, snapshot=snapshot,
        published_by=actor if getattr(actor, "is_authenticated", False) else None,
        note=note[:200],
    )
    website.is_published = True
    website.published_at = timezone.now()
    website.published_snapshot = snapshot
    website.published_version = number
    website.save(update_fields=[
        "is_published", "published_at", "published_snapshot", "published_version", "updated_at",
    ])
    _audit(website.hostel, actor, f"Website published (v{number})", {"version": number})
    return version


def unpublish_website(website: Website, actor=None) -> Website:
    """Take the public site offline (draft + history stay intact)."""
    website.is_published = False
    website.save(update_fields=["is_published", "updated_at"])
    _audit(website.hostel, actor, "Website unpublished")
    return website


@transaction.atomic
def restore_version(website: Website, number: int, actor=None) -> Website:
    """Copy a version's snapshot back into the draft (does NOT auto-publish —
    the owner previews the restored draft, then publishes)."""
    version = WebsiteVersion.objects.get(website=website, number=number)
    snap = version.snapshot or {}

    website.theme = snap.get("theme", {})
    website.seo = snap.get("seo", {})
    website.branding = snap.get("branding", {})
    website.navigation = snap.get("navigation", {})
    website.footer = snap.get("footer", {})
    website.social = snap.get("social", {})
    website.save(update_fields=[
        "theme", "seo", "branding", "navigation", "footer", "social", "updated_at",
    ])

    website.sections.all().delete()
    for entry in snap.get("sections", []):
        if entry.get("type") not in SECTION_TYPES:
            continue  # a type removed from the registry can't be restored
        WebsiteSection.objects.create(
            website=website,
            type=entry["type"],
            order=int(entry.get("order", 0)),
            is_visible=bool(entry.get("is_visible", True)),
            content=entry.get("content", {}),
        )
    _audit(website.hostel, actor, f"Website draft restored from v{number}", {"version": number})
    return website


def public_payload(website: Website, hostel) -> dict:
    """What the public renderer receives: the live snapshot + workspace identity."""
    from apps.domains.services import public_url_for
    from apps.tenants.branding import white_label

    snapshot = website.published_snapshot or {}
    sections = [
        s for s in snapshot.get("sections", []) if s.get("is_visible", True)
    ]
    return {
        "workspace": {
            "name": hostel.name,
            "username": hostel.slug,
            "url": hostel.workspace_url,
            # Canonical public URL: the primary custom domain when one is
            # active (Prompt 05) — drives SEO tags and the default-host 301.
            "public_url": public_url_for(hostel),
        },
        "white_label": white_label(hostel),
        "published": website.is_published,
        "published_at": website.published_at,
        "version": website.published_version,
        "theme": snapshot.get("theme", {}),
        "seo": snapshot.get("seo", {}),
        "branding": snapshot.get("branding", {}),
        "navigation": snapshot.get("navigation", {}),
        "footer": snapshot.get("footer", {}),
        "social": snapshot.get("social", {}),
        "sections": sorted(sections, key=lambda s: s.get("order", 0)),
    }


def overview(website: Website) -> dict:
    """Builder dashboard numbers."""
    sections = list(website.sections.all())
    present_types = {s.type for s in sections}
    missing = [
        t for t, cfg in SECTION_TYPES.items()
        if cfg.get("recommended") and t not in present_types
    ]
    draft_snapshot = build_snapshot(website)
    has_unpublished_changes = (
        website.is_published and draft_snapshot != (website.published_snapshot or {})
    )
    inquiries = WebsiteInquiry.objects.filter(hostel=website.hostel)
    seo = website.effective_seo()
    seo_checks = {
        "meta_title": bool(seo.get("meta_title")),
        "meta_description": bool(seo.get("meta_description")),
        "og_image": bool(seo.get("og_image") or website.effective_branding().get("social_image")),
    }
    return {
        "is_published": website.is_published,
        "published_at": website.published_at,
        "published_version": website.published_version,
        "has_unpublished_changes": has_unpublished_changes,
        "section_count": len(sections),
        "visible_section_count": sum(1 for s in sections if s.is_visible),
        "missing_sections": missing,
        "seo_score": round(100 * sum(seo_checks.values()) / len(seo_checks)),
        "seo_checks": seo_checks,
        "inquiry_count": inquiries.count(),
        "new_inquiry_count": inquiries.filter(status=WebsiteInquiry.Status.NEW).count(),
        "version_count": website.versions.count(),
    }
