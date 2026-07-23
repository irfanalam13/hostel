"""Super-Admin operations-governance API (mounted at /api/platform/ops/).

Backs the operator dashboard: system announcements, scheduled maintenance,
incident tracking, and the feature-flag engine. Every endpoint is gated by
``IsPlatformAdmin`` (Django ``is_superuser``); every mutation is audited.
"""
import logging

from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.subscriptions.permissions import IsPlatformAdmin

from . import services
from .models import (
    Announcement,
    FeatureFlag,
    FeatureFlagOverride,
    Incident,
    IncidentUpdate,
    MaintenanceWindow,
)
from .serializers import (
    AnnouncementSerializer,
    FeatureFlagOverrideSerializer,
    FeatureFlagSerializer,
    IncidentSerializer,
    IncidentUpdateSerializer,
    MaintenanceWindowSerializer,
)

logger = logging.getLogger("apps.platformops")


class _AuditedViewSet(viewsets.ModelViewSet):
    """ModelViewSet that stamps created_by and writes an audit event on writes."""

    permission_classes = [IsPlatformAdmin]
    audit_entity = "platformops"
    audit_action = AuditEvent.Action.UPDATE

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user)
        self._audit("create", obj, AuditEvent.Action.CREATE)

    def perform_update(self, serializer):
        obj = serializer.save()
        self._audit("update", obj, AuditEvent.Action.UPDATE)

    def perform_destroy(self, instance):
        self._audit("delete", instance, AuditEvent.Action.DELETE)
        instance.delete()

    def _audit(self, verb, obj, action_choice):
        record_event(
            self.request,
            action=action_choice,
            actor=self.request.user,
            entity_type=self.audit_entity,
            entity_id=str(getattr(obj, "pk", "")),
            message=f"{verb} {self.audit_entity} {getattr(obj, 'pk', '')}",
        )


class AnnouncementViewSet(_AuditedViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    audit_entity = "announcement"


class MaintenanceWindowViewSet(_AuditedViewSet):
    queryset = MaintenanceWindow.objects.all()
    serializer_class = MaintenanceWindowSerializer
    audit_entity = "maintenance_window"

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        window = self.get_object()
        services.start_maintenance(window, user=request.user, request=request)
        record_event(request, action=AuditEvent.Action.MAINTENANCE, actor=request.user,
                     entity_type="maintenance_window", entity_id=str(window.pk),
                     message=f"maintenance started: {window.title}")
        return Response(self.get_serializer(window).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        window = self.get_object()
        services.complete_maintenance(window, user=request.user, request=request)
        record_event(request, action=AuditEvent.Action.MAINTENANCE, actor=request.user,
                     entity_type="maintenance_window", entity_id=str(window.pk),
                     message=f"maintenance completed: {window.title}")
        return Response(self.get_serializer(window).data)


class IncidentViewSet(_AuditedViewSet):
    queryset = Incident.objects.prefetch_related("updates").all()
    serializer_class = IncidentSerializer
    audit_entity = "incident"

    def _log(self, request, incident, message):
        record_event(request, action=AuditEvent.Action.INCIDENT, actor=request.user,
                     entity_type="incident", entity_id=str(incident.pk), message=message[:255])

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user)
        # Seed the timeline with an opening entry.
        IncidentUpdate.objects.create(
            incident=obj, status=obj.status,
            message=obj.summary or "Incident opened.", created_by=self.request.user,
        )
        self._log(self.request, obj, f"incident opened: {obj.title}")

    @action(detail=True, methods=["post"], url_path="updates")
    def add_update(self, request, pk=None):
        incident = self.get_object()
        serializer = IncidentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        update = serializer.save(incident=incident, created_by=request.user)

        incident.status = new_status
        fields = ["status", "updated_at"]
        if new_status == Incident.Status.RESOLVED and incident.resolved_at is None:
            incident.resolved_at = timezone.now()
            fields.append("resolved_at")
        incident.save(update_fields=fields)

        self._log(request, incident, f"incident update ({new_status}): {update.message}")
        return Response(IncidentSerializer(incident).data, status=status.HTTP_201_CREATED)


class FeatureFlagViewSet(_AuditedViewSet):
    queryset = FeatureFlag.objects.prefetch_related("overrides").all()
    serializer_class = FeatureFlagSerializer
    audit_entity = "feature_flag"

    def _flag_audit(self, request, flag, message):
        record_event(request, action=AuditEvent.Action.FEATURE_FLAG, actor=request.user,
                     entity_type="feature_flag", entity_id=str(flag.pk), message=message[:255])

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user)
        self._flag_audit(self.request, obj, f"flag created: {obj.key}")

    def perform_update(self, serializer):
        obj = serializer.save()
        self._flag_audit(self.request, obj,
                         f"flag updated: {obj.key} (active={obj.is_active}, "
                         f"kill={obj.kill}, rollout={obj.rollout_percentage})")

    @action(detail=True, methods=["post"], url_path="kill")
    def kill_switch(self, request, pk=None):
        """Emergency per-flag kill switch (force OFF for everyone)."""
        flag = self.get_object()
        flag.kill = bool(request.data.get("kill", True))
        flag.save(update_fields=["kill", "updated_at"])
        self._flag_audit(request, flag, f"flag kill={flag.kill}: {flag.key}")
        return Response(self.get_serializer(flag).data)

    @action(detail=True, methods=["post"], url_path="overrides")
    def add_override(self, request, pk=None):
        flag = self.get_object()
        serializer = FeatureFlagOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        override = serializer.save(flag=flag, created_by=request.user)
        self._flag_audit(request, flag,
                         f"override set on {flag.key} -> {override.enabled}")
        return Response(FeatureFlagOverrideSerializer(override).data,
                        status=status.HTTP_201_CREATED)


class FeatureFlagOverrideViewSet(_AuditedViewSet):
    queryset = FeatureFlagOverride.objects.select_related("flag", "user").all()
    serializer_class = FeatureFlagOverrideSerializer
    audit_entity = "feature_flag_override"
    audit_action = AuditEvent.Action.FEATURE_FLAG

    def get_queryset(self):
        qs = super().get_queryset()
        flag = self.request.query_params.get("flag")
        if flag:
            qs = qs.filter(flag_id=flag)
        return qs

    def _override_audit(self, override, message):
        record_event(self.request, action=AuditEvent.Action.FEATURE_FLAG, actor=self.request.user,
                     entity_type="feature_flag_override", entity_id=str(override.pk),
                     message=message[:255])

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user)
        self._override_audit(obj, f"override created on {obj.flag.key} -> {obj.enabled}")

    def perform_update(self, serializer):
        obj = serializer.save()
        self._override_audit(obj, f"override updated on {obj.flag.key} -> {obj.enabled}")

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        """Deactivate an override without deleting it (keeps the audit trail)."""
        override = self.get_object()
        override.is_active = False
        override.save(update_fields=["is_active", "updated_at"])
        self._override_audit(override, f"override revoked on {override.flag.key}")
        return Response(self.get_serializer(override).data)

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        override = self.get_object()
        override.is_active = True
        override.save(update_fields=["is_active", "updated_at"])
        self._override_audit(override, f"override reactivated on {override.flag.key}")
        return Response(self.get_serializer(override).data)


class HostelLookupView(APIView):
    """Typeahead for the override builder's tenant selector (super-admin)."""

    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        from apps.tenants.models import Hostel

        q = (request.query_params.get("q") or "").strip()
        qs = Hostel.objects.filter(is_deleted=False)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
        results = [
            {"id": str(h.id), "label": f"{h.name} ({h.code})", "code": h.code}
            for h in qs.order_by("name")[:20]
        ]
        return Response({"results": results})


class UserLookupView(APIView):
    """Typeahead for the override builder's user selector (super-admin)."""

    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        from apps.accounts.models import User

        q = (request.query_params.get("q") or "").strip()
        qs = User.objects.all()
        if q:
            qs = qs.filter(
                Q(email__icontains=q) | Q(username__icontains=q)
                | Q(first_name__icontains=q) | Q(last_name__icontains=q)
            )
        results = []
        for u in qs.order_by("email")[:20]:
            name = (u.get_full_name() or "").strip()
            results.append({
                "id": u.pk,
                "label": name or u.email or u.username,
                "email": u.email,
                "role": u.role,
            })
        return Response({"results": results})
