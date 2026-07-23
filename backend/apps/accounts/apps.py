from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'apps.accounts'

    def ready(self):
        # Membership lookups are cached (apps.common.permissions); drop the
        # cached entry whenever a user↔hostel link changes so revoking or
        # granting access takes effect on the next request, not after the TTL.
        from django.db.models.signals import post_delete, post_save

        from apps.common.permissions import invalidate_membership_cache

        from .models import UserHostel

        def _invalidate(sender, instance, **kwargs):
            invalidate_membership_cache(instance.user_id, instance.hostel_id)

        post_save.connect(_invalidate, sender=UserHostel,
                          dispatch_uid="accounts.membership_cache.save")
        post_delete.connect(_invalidate, sender=UserHostel,
                            dispatch_uid="accounts.membership_cache.delete")
