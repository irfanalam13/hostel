import csv

import django_filters
from django.http import StreamingHttpResponse
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsHostelResolved, IsOwnerOrManager, IsSuperUser

from .integrity import verify_chain
from .models import AuditEvent
from .serializers import AuditEventSerializer


class AuditEventFilter(django_filters.FilterSet):
    created_after = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = AuditEvent
        fields = {
            "action": ["exact", "in"],
            "result": ["exact"],
            "entity_type": ["exact"],
            "entity_id": ["exact"],
            "actor": ["exact"],
            "request_id": ["exact"],
        }


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only, filterable, exportable, tamper-evident audit trail.

    Always scoped to the caller's workspace: an owner/manager only ever sees
    their own tenant's events (membership enforced by ``IsHostelResolved``),
    while platform admins (superusers) see everything. Previously an unscoped
    ``.all()`` behind only a role check leaked events across tenants.
    """

    serializer_class = AuditEventSerializer
    permission_classes = [IsHostelResolved, IsOwnerOrManager]
    filterset_class = AuditEventFilter
    filter_backends = [
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["message", "reason", "entity_id", "entity_type"]
    ordering_fields = ["created_at", "sequence", "action", "result"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = AuditEvent.objects.select_related("actor").all()
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return qs

        # Tenant isolation: prefer the workspace resolved for this request; fall
        # back to every workspace the caller actively belongs to. Never unscoped.
        hostel = getattr(self.request, "hostel", None)
        if hostel is not None:
            return qs.filter(hostel_id=hostel.id)

        from apps.accounts.models import UserHostel

        member_hostel_ids = UserHostel.objects.filter(
            user=user, is_active=True
        ).values_list("hostel_id", flat=True)
        return qs.filter(hostel_id__in=list(member_hostel_ids))

    @action(detail=False, methods=["get"])
    def export(self, request):
        """Stream the current (filtered) view as CSV."""
        queryset = self.filter_queryset(self.get_queryset())
        columns = [
            "id", "sequence", "created_at", "action", "result", "status_code",
            "duration_ms", "actor_id", "hostel_id", "entity_type", "entity_id",
            "message", "reason", "ip_address", "request_id", "content_hash",
        ]

        def rows():
            writer = csv.writer(_Echo())
            yield writer.writerow(columns)
            for event in queryset.iterator():
                yield writer.writerow([getattr(event, c) for c in columns])

        response = StreamingHttpResponse(rows(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit-events.csv"'
        return response

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsSuperUser])
    def verify(self, request):
        """Re-verify the append-only hash chain (platform admins only)."""
        limit = request.query_params.get("limit")
        result = verify_chain(limit=int(limit) if limit and limit.isdigit() else None)
        return Response(result.as_dict())


class _Echo:
    """File-like object that returns the row it is asked to write (for streaming CSV)."""

    def write(self, value):
        return value
