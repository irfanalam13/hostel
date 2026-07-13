"""Admin-only disaster-recovery API.

    POST /api/admin/restore/            run (or dry-run) a restore
    GET  /api/admin/dr/status/          current DR mode + storage + recent runs
    POST /api/admin/dr/mode/            switch DR mode (normal/maintenance/emergency)
    POST /api/admin/backups/<id>/validate/   re-validate a stored backup

Authorization has two tiers:

* **Per-hostel operations** (restore, backup validate) run against one hostel
  and are gated by :class:`IsDRAdmin` (superuser or ADMIN role) *plus* an
  explicit :func:`_can_touch_hostel` membership check — a tenant admin may
  recover their own workspace, never another's.
* **Platform-global operations** (DR mode switch, DR status overview) affect
  every tenant / expose cross-tenant data, so they are super-admin only
  (:class:`IsSuperUser`) — a single tenant's ADMIN must never flip the global
  DR mode or read other tenants' restore history.

Every restore request is audited, requires an explicit backup_id, defaults to
force=false, and a destructive restore additionally requires a confirmation
token equal to the hostel code being overwritten.
"""

import logging

from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserHostel
from apps.common.permissions import IsSuperUser
from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event

from .dr import get_mode, set_mode
from .models import BackupSnapshot, DRMode, RestoreRun
from .restore import RestoreError, RestoreSafetyError, RestoreValidationError, restore_hostel
from .retention import storage_usage
from .validation import validate_backup

logger = logging.getLogger("apps.backups")


class IsDRAdmin(BasePermission):
    """Superuser or users with the ADMIN role."""

    message = "Disaster-recovery operations require an administrator."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return bool(user.is_superuser or getattr(user, "role", None) == "ADMIN")


def _can_touch_hostel(user, hostel) -> bool:
    if user.is_superuser:
        return True
    return UserHostel.objects.filter(user=user, hostel=hostel, is_active=True).exists()


class AdminRestoreView(APIView):
    permission_classes = [IsAuthenticated, IsDRAdmin]
    throttle_scope = "backup"

    def post(self, request):
        backup_id = request.data.get("backup_id")
        dry_run = bool(request.data.get("dry_run", False))
        force = bool(request.data.get("force", False))
        confirm = request.data.get("confirm", "")

        # Always audit the request itself, before doing anything.
        record_event(
            request, action=AuditEvent.Action.RESTORE, actor=request.user,
            entity_type="backup.restore.request", entity_id=str(backup_id or ""),
            message=f"Restore requested (dry_run={dry_run}, force={force})",
            meta={"backup_id": str(backup_id or ""), "dry_run": dry_run, "force": force},
        )

        if not backup_id:
            return Response({"detail": "backup_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            snap = BackupSnapshot.objects.select_related("hostel").get(id=backup_id)
        except (BackupSnapshot.DoesNotExist, ValueError, Exception):
            return Response({"detail": "Backup not found."}, status=status.HTTP_404_NOT_FOUND)

        hostel = snap.hostel
        if not _can_touch_hostel(request.user, hostel):
            return Response(
                {"detail": "You are not allowed to restore this hostel."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Safety gate for destructive restores: force + matching confirmation token.
        if not dry_run:
            if not force:
                return Response(
                    {"detail": "Destructive restore requires force=true (or use dry_run=true)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if confirm != hostel.code:
                return Response(
                    {
                        "detail": "Confirmation token mismatch. Set 'confirm' to the hostel code "
                        f"('{hostel.code}') to authorise overwriting its data.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            run = restore_hostel(
                hostel, source_snapshot=snap, user=request.user, request=request,
                dry_run=dry_run, force=force,
            )
        except (RestoreValidationError, RestoreSafetyError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RestoreError as exc:
            return Response(
                {"detail": f"Restore failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "run_id": str(run.id),
                "status": run.status,
                "dry_run": run.dry_run,
                "hostel": hostel.code,
                "backup_id": str(snap.id),
                "pre_restore_snapshot": str(run.pre_restore_snapshot_id or "") or None,
                "stats": run.stats,
            }
        )


class DRStatusView(APIView):
    # Platform-global: exposes the DR mode, aggregate storage and cross-tenant
    # restore history. Super-admin only — a tenant ADMIN must not see other
    # tenants' restore runs (previously an IsDRAdmin cross-tenant metadata leak).
    permission_classes = [IsAuthenticated, IsSuperUser]

    def get(self, request):
        recent = RestoreRun.objects.order_by("-created_at")[:10]
        return Response(
            {
                "mode": get_mode(),
                "storage": storage_usage(),
                "recent_restores": [
                    {
                        "id": str(r.id),
                        "hostel_id": str(r.hostel_id),
                        "status": r.status,
                        "dry_run": r.dry_run,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in recent
                ],
            }
        )


class DRModeView(APIView):
    # Platform-global: switching DR mode (normal/maintenance/emergency) affects
    # every tenant, so it is super-admin only — a single tenant's ADMIN must
    # never be able to put the whole SaaS into maintenance/emergency mode.
    permission_classes = [IsAuthenticated, IsSuperUser]

    def post(self, request):
        mode = request.data.get("mode")
        reason = request.data.get("reason", "")
        if mode not in DRMode.values:
            return Response(
                {"detail": f"mode must be one of {DRMode.values}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        state = set_mode(mode, reason=reason, user=request.user, request=request)
        return Response({"mode": state.mode, "reason": state.reason})


class BackupValidateView(APIView):
    permission_classes = [IsAuthenticated, IsDRAdmin]

    def post(self, request, pk=None):
        try:
            snap = BackupSnapshot.objects.get(id=pk)
        except (BackupSnapshot.DoesNotExist, ValueError, Exception):
            return Response({"detail": "Backup not found."}, status=status.HTTP_404_NOT_FOUND)
        if not _can_touch_hostel(request.user, snap.hostel):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        report = validate_backup(snap, persist=True)
        return Response({"backup_id": str(snap.id), "valid": report["ok"], "report": report})
