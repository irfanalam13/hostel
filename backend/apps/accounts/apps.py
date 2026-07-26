from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'apps.accounts'

    def ready(self):
        # Membership lookups are cached (apps.common.permissions); drop the
        # cached entry whenever a user↔hostel link changes so revoking or
        # granting access takes effect on the next request, not after the TTL.
        from django.db.models.signals import post_delete, post_save

        from apps.common.permissions import invalidate_membership_cache

        from .models import User, UserHostel

        def _invalidate(sender, instance, **kwargs):
            invalidate_membership_cache(instance.user_id, instance.hostel_id)

        post_save.connect(_invalidate, sender=UserHostel,
                          dispatch_uid="accounts.membership_cache.save")
        post_delete.connect(_invalidate, sender=UserHostel,
                            dispatch_uid="accounts.membership_cache.delete")

        # A super-admin (createsuperuser, or is_superuser flipped on later via
        # Django admin) needs a real hostel membership to use the existing
        # hostel-bound JWT pipeline (see docs/AUTHENTICATION.md "Super-admin
        # access") — auto-link them to the one hidden, shared platform
        # workspace instead of requiring a manual UserHostel row.
        def _link_superuser_to_platform_workspace(sender, instance, **kwargs):
            if not instance.is_superuser:
                return
            from apps.tenants.services import get_or_create_platform_workspace

            hostel = get_or_create_platform_workspace()
            UserHostel.objects.get_or_create(
                user=instance, hostel=hostel, defaults={"is_active": True}
            )

        post_save.connect(_link_superuser_to_platform_workspace, sender=User,
                          dispatch_uid="accounts.superuser_platform_link.save")
