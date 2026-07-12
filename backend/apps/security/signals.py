"""Hot reload: any change to runtime security data invalidates the config
snapshot on EVERY container via the shared generation counter."""
import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from . import conf
from .models import IPRule, SecuritySetting

logger = logging.getLogger("apps.security")


@receiver(post_save, sender=SecuritySetting)
@receiver(post_delete, sender=SecuritySetting)
@receiver(post_save, sender=IPRule)
@receiver(post_delete, sender=IPRule)
def _bump_security_config(sender, instance, **kwargs):
    conf.bump()
    logger.info("security config change (%s) — generation bumped",
                sender.__name__)
