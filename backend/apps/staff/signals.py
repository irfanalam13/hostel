"""Keep the custom-role permission cache correct when roles change."""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Role
from .rbac import invalidate_role_cache


@receiver(post_save, sender=Role)
@receiver(post_delete, sender=Role)
def _invalidate_role_perms(sender, instance, **kwargs):
    invalidate_role_cache(instance.pk)
