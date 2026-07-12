from django.apps import AppConfig


class SecurityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.security"
    label = "security"
    verbose_name = "Security & Rate Limiting"

    def ready(self):
        from . import checks, signals  # noqa: F401 — register receivers + checks
