from django.apps import AppConfig


class TenantsConfig(AppConfig):
    name = 'apps.tenants'

    def ready(self):
        # Cache invalidation: any tenant change (rename, status, subscription,
        # archive, delete) must drop its cached lookup entries immediately.
        from django.db.models.signals import post_delete, post_save

        from .cache import invalidate_tenant_cache
        from .models import Hostel

        def _invalidate(sender, instance, **kwargs):
            invalidate_tenant_cache(instance)
            # Workspace settings can override role permissions — drop the
            # cached RBAC sets so permission edits apply immediately.
            from apps.common.rbac import invalidate_permissions_cache

            invalidate_permissions_cache(instance.pk)

        post_save.connect(_invalidate, sender=Hostel, dispatch_uid="tenants.cache.save")
        post_delete.connect(_invalidate, sender=Hostel, dispatch_uid="tenants.cache.delete")
