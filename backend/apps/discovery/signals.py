from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review
from .tasks import recompute_hostel_rating


@receiver(post_save, sender=Review)
def _review_saved(sender, instance, **kwargs):
    recompute_hostel_rating.delay(str(instance.hostel_id))


@receiver(post_delete, sender=Review)
def _review_deleted(sender, instance, **kwargs):
    recompute_hostel_rating.delay(str(instance.hostel_id))


@receiver(post_save, sender="tenants.Hostel")
def _hostel_saved(sender, instance, created, **kwargs):
    # Every hostel gets a HostelDiscoveryProfile so it's eligible for the
    # directory by default (auto-listed) — the directory queryset joins on
    # this row, so a missing one would silently exclude the hostel.
    if created and not instance.is_platform_workspace:
        from .services import sync_discovery_profile

        sync_discovery_profile(instance)
