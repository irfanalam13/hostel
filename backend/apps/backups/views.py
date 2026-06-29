import json
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.common.permissions import IsOwner
from apps.tenants.models import Hostel
from .models import BackupSnapshot
from .serializers import BackupSnapshotSerializer
from .tasks import _dump_hostel, scheduled_backup_for_hostel


class BackupViewSet(viewsets.ModelViewSet):
    serializer_class = BackupSnapshotSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    throttle_scope = "backup"

    def _hostels_for_user(self):
        return Hostel.objects.filter(user_links__user=self.request.user, user_links__is_active=True)

    def _get_hostel(self, hostel_id):
        return self._hostels_for_user().get(id=hostel_id)

    def get_queryset(self):
        return BackupSnapshot.objects.filter(hostel__in=self._hostels_for_user()).order_by("-id")

    @action(detail=False, methods=["POST"])
    def create_snapshot(self, request):
        hostel = self._get_hostel(request.data.get("hostel"))
        data = _dump_hostel(hostel)
        payload = json.dumps(data, default=str).encode("utf-8")

        snap = BackupSnapshot(hostel=hostel, kind="manual", note=(request.data.get("note", "")[:255]))
        snap.file.save(f"{hostel.code}_backup_manual.json", ContentFile(payload))
        snap.save()
        record_event(
            request, action=AuditEvent.Action.BACKUP, hostel=hostel,
            entity_type="backup.snapshot", entity_id=snap.id,
            message=f"Manual backup created for {hostel.code}",
        )
        return Response({"id": snap.id, "status": "ok"})

    @action(detail=True, methods=["GET"])
    def download(self, request, pk=None):
        snap = self.get_object()
        resp = HttpResponse(snap.file.read(), content_type="application/json")
        resp["Content-Disposition"] = f'attachment; filename="{snap.file.name.split("/")[-1]}"'
        return resp

    @action(detail=False, methods=["POST"])
    def restore(self, request):
        hostel = self._get_hostel(request.data.get("hostel"))
        raw_json = request.data.get("json")
        if not raw_json:
            return Response({"detail": "json is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Bound the payload so a malicious/oversized upload can't exhaust disk.
        max_bytes = getattr(settings, "MAX_BACKUP_RESTORE_MB", 50) * 1024 * 1024
        if len(raw_json.encode("utf-8")) > max_bytes:
            return Response(
                {"detail": f"Payload exceeds the {max_bytes // (1024 * 1024)} MB limit."},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        try:
            parsed = json.loads(raw_json)
        except Exception:
            return Response({"detail": "Invalid JSON."}, status=status.HTTP_400_BAD_REQUEST)

        # Shape check: a backup is a JSON object (see tasks._dump_hostel), not a
        # bare scalar/array. Reject obviously-wrong payloads early.
        if not isinstance(parsed, dict):
            return Response(
                {"detail": "Backup payload must be a JSON object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Restore import is intentionally conservative here: keep the uploaded
        # payload as a snapshot so an owner can download/audit it before any
        # destructive data replacement is added.
        snap = BackupSnapshot(hostel=hostel, kind="manual", note="Imported restore payload")
        snap.file.save(f"{hostel.code}_restore_import.json", ContentFile(raw_json.encode("utf-8")))
        snap.save()
        record_event(
            request, action=AuditEvent.Action.RESTORE, hostel=hostel,
            entity_type="backup.snapshot", entity_id=snap.id,
            message=f"Restore payload stored for {hostel.code}",
        )
        return Response({"status": "stored", "id": snap.id})

    @action(detail=False, methods=["POST"])
    def schedule_now(self, request):
        hostel = self._get_hostel(request.data.get("hostel"))
        scheduled_backup_for_hostel.delay(hostel.id)
        return Response({"status": "scheduled"})
