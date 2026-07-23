from django.apps import AppConfig


class PlatformOpsConfig(AppConfig):
    name = "apps.platformops"
    verbose_name = "Platform Operations"

    def ready(self):
        from . import signals  # noqa: F401  (register cache-invalidation signals)
