"""Celery beat tasks for operations governance."""
import logging

from celery import shared_task

logger = logging.getLogger("apps.platformops")


@shared_task
def transition_maintenance_windows():
    from .services import auto_transition_windows

    summary = auto_transition_windows()
    if summary["started"] or summary["completed"]:
        logger.info("maintenance transitions: %s", summary)
    return summary


@shared_task
def reap_feature_overrides():
    from .services import reap_expired_overrides

    return reap_expired_overrides()
