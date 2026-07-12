"""Invalidate cached entitlement snapshots on any change that could affect
them. We bump a single global generation counter (cheap, O(1)) rather than
tracking which hostels a plan touches — plan/catalog edits are rare and this
keeps invalidation correct and simple. See ``entitlements.bump_generation``.
"""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .entitlements import bump_generation, invalidate_hostel
from .models import (
    Feature,
    FeatureOverride,
    LimitDefinition,
    LimitOverride,
    PlanFeature,
    PlanLimit,
)

_WATCHED = (
    PlanFeature,
    PlanLimit,
    Feature,
    LimitDefinition,
    FeatureOverride,
    LimitOverride,
)


@receiver(post_save)
def _bump_on_save(sender, **kwargs):
    if sender in _WATCHED:
        bump_generation()


@receiver(post_delete)
def _bump_on_delete(sender, **kwargs):
    if sender in _WATCHED:
        bump_generation()


@receiver(post_save, sender="tenants.Hostel")
def _invalidate_on_hostel_save(sender, instance, **kwargs):
    # A hostel's plan pointer / plan_name may have changed — drop just its
    # snapshot (targeted, avoids a global bump on routine hostel writes).
    invalidate_hostel(instance)
