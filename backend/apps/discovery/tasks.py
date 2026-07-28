"""Celery task: recompute a hostel's denormalized rating cache."""
import logging

from celery import shared_task
from django.db.models import Avg, Count
from django.utils import timezone

logger = logging.getLogger("apps.discovery")


@shared_task
def recompute_hostel_rating(hostel_id):
    """Recompute average_rating/rating_count/rating_breakdown for one hostel
    from its PUBLISHED reviews. Triggered by a post_save/post_delete signal on
    Review — eventual consistency of a few seconds is acceptable."""
    from .models import HostelDiscoveryProfile, Review

    published = Review.objects.filter(hostel_id=hostel_id, status=Review.Status.PUBLISHED)
    agg = published.aggregate(avg=Avg("rating"))
    count = published.count()
    avg = round(float(agg["avg"] or 0), 1)
    breakdown = {str(n): 0 for n in range(1, 6)}
    for row in published.values("rating").annotate(n=Count("id")):
        breakdown[str(row["rating"])] = row["n"]

    HostelDiscoveryProfile.objects.update_or_create(
        hostel_id=hostel_id,
        defaults={
            "average_rating": avg,
            "rating_count": count,
            "rating_breakdown": breakdown,
            "rating_computed_at": timezone.now(),
        },
    )
    logger.info("recomputed rating for hostel %s: avg=%s count=%s", hostel_id, avg, count)
    return {"hostel_id": str(hostel_id), "average_rating": avg, "rating_count": count}


@shared_task
def self_heal_missing_discovery_data():
    """Back-fill a missing ``Website`` and/or ``HostelDiscoveryProfile`` row
    for any real, active hostel. Both rows are normally created eagerly
    (hostel creation scaffolds a Website — apps.tenants.services — and
    workspace-settings saves sync the discovery profile — apps.tenants.
    workspace_settings._sync_discovery_profile_if_relevant), but both of those
    call sites swallow/log failures rather than raising, so a transient error
    can silently leave a hostel invisible to its own public site and/or the
    cross-hostel directory. This hourly sweep closes that gap."""
    from apps.tenants.models import Hostel
    from apps.website.services import get_or_scaffold_website

    from .models import HostelDiscoveryProfile
    from .services import sync_discovery_profile

    base = Hostel.objects.filter(is_platform_workspace=False, is_active=True, is_deleted=False)

    healed_websites = 0
    for hostel in base.filter(website__isnull=True):
        try:
            get_or_scaffold_website(hostel)
            healed_websites += 1
        except Exception:
            logger.exception("self-heal: website scaffold failed (hostel=%s)", hostel.pk)

    healed_profiles = 0
    for hostel in base.filter(discovery_profile__isnull=True):
        try:
            # is_listed=True mirrors the model's own default (every published
            # website is listed by default; is_listed only ever flips false
            # from the platform side).
            HostelDiscoveryProfile.objects.get_or_create(hostel=hostel, defaults={"is_listed": True})
            sync_discovery_profile(hostel)
            healed_profiles += 1
        except Exception:
            logger.exception("self-heal: discovery profile create failed (hostel=%s)", hostel.pk)

    logger.info(
        "self-heal: created %d missing website(s), %d missing discovery profile(s)",
        healed_websites, healed_profiles,
    )
    return {"websites_created": healed_websites, "profiles_created": healed_profiles}
