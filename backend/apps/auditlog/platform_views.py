"""Super-Admin audit trail — the same tamper-evident event log tenants see,
reachable cross-tenant. ``AuditEventViewSet.get_queryset`` already returns the
fully unscoped queryset for superusers, so this subclass only needs to swap
the permission gate; ``export``/``verify`` actions come along for free.
"""
from apps.subscriptions.permissions import IsPlatformAdmin

from .views import AuditEventViewSet


class PlatformAuditEventViewSet(AuditEventViewSet):
    permission_classes = [IsPlatformAdmin]
