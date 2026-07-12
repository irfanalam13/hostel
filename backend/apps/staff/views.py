"""Staff Management API.

All viewsets are workspace-scoped (``request.hostel``) and permission-gated via
``apps.common.rbac`` (``staff.*`` catalog). Mutations are audit-logged and staff
creation enforces the ``max_staff`` plan quota.
"""
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.common import rbac
from apps.common.permissions import IsHostelResolved
from apps.common.rbac import ActionPermissions
from apps.subscriptions.gates import enforce_limit

from . import services
from .models import Department, Designation, Role, StaffDocument, StaffProfile
from .serializers import (
    DepartmentSerializer,
    DesignationSerializer,
    RoleSerializer,
    StaffCreateSerializer,
    StaffDocumentSerializer,
    StaffProfileSerializer,
)


def _permission_catalog():
    """The full ``module.action`` catalog, grouped by module, for the custom
    role editor. Driven by ``apps.common.rbac`` so new modules appear here
    automatically as later phases land."""
    modules: dict[str, set] = {}
    for m in rbac.MODULES:
        modules.setdefault(m, set()).update(f"{m}.{a}" for a in rbac.CRUD)
    for fp in rbac.FEATURE_PERMISSIONS:
        modules.setdefault(fp.split(".")[0], set()).add(fp)
    return [
        {"module": m, "permissions": sorted(perms)}
        for m, perms in sorted(modules.items())
    ]


class RoleViewSet(ModelViewSet):
    serializer_class = RoleSerializer
    permission_classes = [IsHostelResolved, ActionPermissions]
    permission_map = {
        "list": ["staff.view"], "retrieve": ["staff.view"],
        "create": ["staff.manage_roles"], "update": ["staff.manage_roles"],
        "partial_update": ["staff.manage_roles"], "destroy": ["staff.manage_roles"],
        "catalog": ["staff.view"],
    }

    def get_queryset(self):
        services.ensure_default_roles(self.request.hostel)
        return (
            Role.objects.filter(hostel=self.request.hostel)
            .annotate(staff_count=Count("staff", filter=Q(staff__is_deleted=False)))
            .order_by("-is_system", "name")
        )

    def perform_create(self, serializer):
        role = serializer.save(hostel=self.request.hostel)
        record_event(
            self.request, action=AuditEvent.Action.CREATE, actor=self.request.user,
            hostel=self.request.hostel, entity_type="staff.role", entity_id=role.id,
            message=f"Role created: {role.name}",
        )

    def perform_update(self, serializer):
        role = serializer.save()
        record_event(
            self.request, action=AuditEvent.Action.UPDATE, actor=self.request.user,
            hostel=self.request.hostel, entity_type="staff.role", entity_id=role.id,
            message=f"Role updated: {role.name}",
        )

    def perform_destroy(self, instance):
        if instance.is_system:
            raise ValidationError({"detail": "System roles cannot be deleted (you can deactivate them)."})
        name = instance.name
        rid = instance.id
        instance.delete()
        record_event(
            self.request, action=AuditEvent.Action.DELETE, actor=self.request.user,
            hostel=self.request.hostel, entity_type="staff.role", entity_id=rid,
            message=f"Role deleted: {name}",
        )

    @action(detail=False, methods=["get"])
    def catalog(self, request):
        """Permission catalog for the role editor."""
        return Response({"modules": _permission_catalog()})


class DepartmentViewSet(ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [IsHostelResolved, ActionPermissions]
    permission_map = {
        "list": ["staff.view"], "retrieve": ["staff.view"],
        "create": ["staff.manage_departments"], "update": ["staff.manage_departments"],
        "partial_update": ["staff.manage_departments"], "destroy": ["staff.manage_departments"],
    }

    def get_queryset(self):
        return (
            Department.objects.filter(hostel=self.request.hostel)
            .select_related("head")
            .annotate(staff_count=Count("staff", filter=Q(staff__is_deleted=False)))
            .order_by("name")
        )

    def perform_create(self, serializer):
        enforce_limit(self.request.hostel, "max_departments")
        dept = serializer.save(hostel=self.request.hostel)
        record_event(
            self.request, action=AuditEvent.Action.CREATE, actor=self.request.user,
            hostel=self.request.hostel, entity_type="staff.department", entity_id=dept.id,
            message=f"Department created: {dept.name}",
        )


class DesignationViewSet(ModelViewSet):
    serializer_class = DesignationSerializer
    permission_classes = [IsHostelResolved, ActionPermissions]
    permission_map = {
        "list": ["staff.view"], "retrieve": ["staff.view"],
        "create": ["staff.manage_departments"], "update": ["staff.manage_departments"],
        "partial_update": ["staff.manage_departments"], "destroy": ["staff.manage_departments"],
    }

    def get_queryset(self):
        return (
            Designation.objects.filter(hostel=self.request.hostel)
            .select_related("department")
            .order_by("title")
        )

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel)


class StaffDocumentViewSet(ModelViewSet):
    serializer_class = StaffDocumentSerializer
    permission_classes = [IsHostelResolved, ActionPermissions]
    permission_map = {
        "list": ["staff.view"], "retrieve": ["staff.view"],
        "create": ["staff.edit"], "update": ["staff.edit"],
        "partial_update": ["staff.edit"], "destroy": ["staff.edit"],
    }
    filterset_fields = ["staff", "doc_type"]

    def get_queryset(self):
        return (
            StaffDocument.objects.filter(hostel=self.request.hostel)
            .select_related("staff")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        doc = serializer.save(hostel=self.request.hostel, uploaded_by=self.request.user)
        record_event(
            self.request, action=AuditEvent.Action.CREATE, actor=self.request.user,
            hostel=self.request.hostel, entity_type="staff.document", entity_id=doc.id,
            message=f"Staff document uploaded ({doc.get_doc_type_display()})",
            meta={"staff": str(doc.staff_id)},
        )


class StaffViewSet(ModelViewSet):
    permission_classes = [IsHostelResolved, ActionPermissions]
    permission_map = {
        "list": ["staff.view"], "retrieve": ["staff.view"],
        "create": ["staff.create"], "update": ["staff.edit"],
        "partial_update": ["staff.edit"], "destroy": ["staff.delete"],
        "suspend": ["staff.edit"], "activate": ["staff.edit"], "disable": ["staff.edit"],
        "lock": ["staff.edit"], "unlock": ["staff.edit"], "restore": ["staff.edit"],
        "reset_password": ["staff.reset_password"],
        "force_password_reset": ["staff.reset_password"],
    }
    filterset_fields = ["status", "department", "designation", "role", "employment_type"]
    search_fields = ["first_name", "last_name", "employee_id", "user__username", "user__email"]
    ordering_fields = ["created_at", "employee_id", "joining_date"]

    def get_serializer_class(self):
        return StaffCreateSerializer if self.action == "create" else StaffProfileSerializer

    def get_queryset(self):
        qs = (
            StaffProfile.objects.filter(hostel=self.request.hostel)
            .select_related("user", "role", "department", "designation", "reporting_manager")
            .prefetch_related("documents")
            .order_by("-created_at")
        )
        include_deleted = str(self.request.query_params.get("include_deleted", "")).lower() in (
            "1", "true", "yes",
        )
        # Detail-level lifecycle (e.g. restore) must reach soft-deleted rows.
        if self.action in ("restore", "retrieve") or include_deleted:
            return qs
        return qs.filter(is_deleted=False)

    # --- Create: provision account + profile via the service --------------- #
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enforce_limit(request.hostel, "max_staff")
        profile, temp_password = services.create_staff(
            hostel=request.hostel, actor=request.user, validated=dict(serializer.validated_data)
        )
        services.send_invite_email(
            request.hostel,
            username=profile.user.username,
            email=profile.user.email,
            temp_password=temp_password,
        )
        record_event(
            request, action=AuditEvent.Action.CREATE, actor=request.user,
            hostel=request.hostel, entity_type="staff.profile", entity_id=profile.id,
            message=f"Staff created: {profile.full_name} ({profile.employee_id})",
            meta={"username": profile.user.username, "account_role": profile.user.role},
        )
        data = StaffProfileSerializer(profile, context=self.get_serializer_context()).data
        # Shown once to the creator; also emailed when an address was supplied.
        data["temporary_password"] = temp_password
        return Response(data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        profile = serializer.save()
        record_event(
            self.request, action=AuditEvent.Action.UPDATE, actor=self.request.user,
            hostel=self.request.hostel, entity_type="staff.profile", entity_id=profile.id,
            message=f"Staff updated: {profile.full_name}",
        )

    def perform_destroy(self, instance):
        """Soft delete: preserve the account/history, free the plan seat."""
        from apps.accounts.models import UserHostel

        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
        UserHostel.objects.filter(hostel=instance.hostel, user=instance.user).update(is_active=False)
        record_event(
            self.request, action=AuditEvent.Action.DELETE, actor=self.request.user,
            hostel=self.request.hostel, entity_type="staff.profile", entity_id=instance.id,
            message=f"Staff removed (soft delete): {instance.full_name}",
        )

    # --- Lifecycle actions ------------------------------------------------- #
    def _transition(self, request, status_value, message, event=AuditEvent.Action.UPDATE):
        profile = self.get_object()
        services.set_status(profile, status_value)
        record_event(
            request, action=event, actor=request.user, hostel=request.hostel,
            entity_type="staff.profile", entity_id=profile.id,
            message=f"{message}: {profile.full_name}",
        )
        return Response(StaffProfileSerializer(profile, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        return self._transition(request, StaffProfile.Status.SUSPENDED, "Staff suspended")

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        return self._transition(request, StaffProfile.Status.ACTIVE, "Staff activated")

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):
        return self._transition(request, StaffProfile.Status.DISABLED, "Staff disabled")

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        return self._transition(request, StaffProfile.Status.LOCKED, "Staff account locked")

    @action(detail=True, methods=["post"])
    def unlock(self, request, pk=None):
        return self._transition(request, StaffProfile.Status.ACTIVE, "Staff account unlocked")

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        """Undo a soft delete and reactivate workspace membership."""
        from apps.accounts.models import UserHostel

        profile = self.get_object()
        if not profile.is_deleted:
            raise ValidationError({"detail": "This staff member is not deleted."})
        # Re-provisioning a seat must respect the plan quota.
        enforce_limit(request.hostel, "max_staff")
        profile.is_deleted = False
        profile.deleted_at = None
        profile.status = StaffProfile.Status.ACTIVE
        profile.save(update_fields=["is_deleted", "deleted_at", "status", "updated_at"])
        UserHostel.objects.filter(hostel=request.hostel, user=profile.user).update(is_active=True)
        record_event(
            request, action=AuditEvent.Action.UPDATE, actor=request.user, hostel=request.hostel,
            entity_type="staff.profile", entity_id=profile.id,
            message=f"Staff restored: {profile.full_name}",
        )
        return Response(StaffProfileSerializer(profile, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        profile = self.get_object()
        force = str(request.data.get("force_change", "true")).lower() in ("1", "true", "yes")
        temp = services.reset_password(profile, force_change=force)
        services.send_invite_email(
            request.hostel, username=profile.user.username,
            email=profile.user.email, temp_password=temp,
        )
        record_event(
            request, action=AuditEvent.Action.UPDATE, actor=request.user, hostel=request.hostel,
            entity_type="staff.profile", entity_id=profile.id,
            message=f"Staff password reset: {profile.full_name}",
        )
        return Response({"detail": "Password reset.", "temporary_password": temp})

    @action(detail=True, methods=["post"], url_path="force-password-reset")
    def force_password_reset(self, request, pk=None):
        """Flag the account so the next login requires a password change."""
        profile = self.get_object()
        profile.must_change_password = True
        profile.save(update_fields=["must_change_password", "updated_at"])
        record_event(
            request, action=AuditEvent.Action.UPDATE, actor=request.user, hostel=request.hostel,
            entity_type="staff.profile", entity_id=profile.id,
            message=f"Forced password reset flagged: {profile.full_name}",
        )
        return Response(StaffProfileSerializer(profile, context=self.get_serializer_context()).data)
