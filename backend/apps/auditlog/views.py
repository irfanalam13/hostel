from rest_framework import viewsets
from apps.common.permissions import IsHostelResolved, IsOwnerOrManager
from .models import AuditEvent
from .serializers import AuditEventSerializer


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Audit trail, always scoped to the caller's workspace.

    Previously this exposed ``AuditEvent.objects.all()`` with only a role check
    (``IsOwnerOrManager``), so an owner/manager of one workspace could read
    every tenant's events — a cross-tenant leak. Events are now filtered to the
    hostel(s) the caller is an active member of (superusers see everything, for
    platform operations), and membership is required (``IsHostelResolved``).
    """

    serializer_class = AuditEventSerializer
    permission_classes = [IsHostelResolved, IsOwnerOrManager]

    def get_queryset(self):
        base = AuditEvent.objects.all().order_by("-created_at")
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return base

        # Prefer the workspace resolved for this request; fall back to every
        # workspace the caller actively belongs to. Never unscoped.
        from apps.accounts.models import UserHostel

        hostel = getattr(self.request, "hostel", None)
        if hostel is not None:
            return base.filter(hostel_id=hostel.id)

        member_hostel_ids = UserHostel.objects.filter(
            user=user, is_active=True
        ).values_list("hostel_id", flat=True)
        return base.filter(hostel_id__in=list(member_hostel_ids))
