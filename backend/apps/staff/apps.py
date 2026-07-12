from django.apps import AppConfig


class StaffConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.staff"
    verbose_name = "Staff Management"

    def ready(self):
        # Signal handlers keep the RBAC permission cache correct when a custom
        # role's grants change or a staff member's role assignment moves.
        from . import signals  # noqa: F401
