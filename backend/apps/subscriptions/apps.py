from django.apps import AppConfig


class SubscriptionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.subscriptions"
    verbose_name = "Subscriptions & Plans"

    def ready(self):
        # Connect entitlement-cache invalidation signals.
        from . import signals  # noqa: F401
