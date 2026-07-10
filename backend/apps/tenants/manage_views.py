"""Workspace Management API (Prompt 04) — the owner's console.

Everything operates on ``request.hostel`` (the workspace the session is
bound to), so tenant isolation is inherited from the auth stack. Reads need
``workspace.view``; configuration writes need ``workspace.manage``; team
management needs ``accounts.*``; rename and the danger zone are owner-only
and require the account password.
"""
import logging
import secrets

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.common.permissions import IsOwner, STAFF_ROLES
from apps.common.rbac import RequirePermission

from . import services, workspace_settings
from .models import Hostel
from .serializers import WorkspaceSerializer

logger = logging.getLogger(__name__)

CanView = RequirePermission("workspace.view")
CanManage = RequirePermission("workspace.manage")
CanInvite = RequirePermission("accounts.invite")


def _require_password(request):
    """Danger-zone guard: the acting user must re-enter their password."""
    password = str(request.data.get("password") or "")
    if not password or not request.user.check_password(password):
        raise ValidationError({"password": "Enter your account password to confirm."})


# --------------------------------------------------------------------------- #
# Overview
# --------------------------------------------------------------------------- #
class WorkspaceOverviewView(APIView):
    permission_classes = [IsAuthenticated, CanView]

    def get(self, request):
        from apps.accounts.models import UserHostel
        from apps.website.models import WebsiteInquiry, WebsiteMedia

        hostel = request.hostel
        links = UserHostel.objects.filter(hostel=hostel, is_active=True).select_related("user")
        role_of = lambda link: getattr(link.user, "role", "")  # noqa: E731

        member_count = links.count()
        staff_count = sum(1 for l in links if role_of(l) in STAFF_ROLES)
        student_count = sum(1 for l in links if role_of(l) in {"STUDENT", "RESIDENT"})
        parent_count = sum(1 for l in links if role_of(l) == "PARENT")
        month_ago = timezone.now() - timezone.timedelta(days=30)
        active_users = sum(
            1 for l in links if l.user.last_login and l.user.last_login >= month_ago
        )
        last_login = links.aggregate(latest=Max("user__last_login"))["latest"]

        try:
            from apps.residents.models import Resident

            resident_count = Resident.objects.filter(hostel=hostel).count()
        except Exception:
            resident_count = 0

        # Storage: website assets (best effort — a missing file must not 500).
        storage_bytes = 0
        for media in WebsiteMedia.objects.filter(hostel=hostel):
            try:
                storage_bytes += media.file.size
            except Exception:
                continue

        trial_days_left = None
        if hostel.trial_ends_at:
            trial_days_left = max((hostel.trial_ends_at - timezone.localdate()).days, 0)

        return Response({
            "workspace": WorkspaceSerializer(hostel).data,
            "owner": getattr(hostel.owner, "username", None) or hostel.owner_name,
            "counts": {
                "members": member_count,
                "staff": staff_count,
                "students": student_count,
                "parents": parent_count,
                "residents": resident_count,
                "active_users_30d": active_users,
            },
            "last_login": last_login,
            "storage_bytes": storage_bytes,
            "subscription": {
                "plan": hostel.plan_name,
                "status": hostel.status,
                "trial_ends_at": hostel.trial_ends_at,
                "trial_days_left": trial_days_left,
                "active_until": hostel.subscription_active_until,
            },
            "inquiries": WebsiteInquiry.objects.filter(hostel=hostel).count(),
        })


# --------------------------------------------------------------------------- #
# Namespaced settings (profile / business / regional / notifications /
# security / preferences / branding)
# --------------------------------------------------------------------------- #
class WorkspaceSettingsNamespaceView(APIView):
    permission_classes = [IsAuthenticated, CanView]

    def get(self, request, namespace: str):
        try:
            return Response({
                "namespace": namespace,
                "settings": workspace_settings.get_workspace_settings(request.hostel, namespace),
                "defaults": workspace_settings.namespace_defaults(namespace),
            })
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else str(exc))

    def patch(self, request, namespace: str):
        if not CanManage().has_permission(request, self):
            return Response({"detail": "You do not have permission to change workspace settings."},
                            status=status.HTTP_403_FORBIDDEN)
        try:
            updated = workspace_settings.update_workspace_settings(
                request.hostel, namespace, request.data, actor=request.user
            )
        except DjangoValidationError as exc:
            raise ValidationError(getattr(exc, "message_dict", None) or list(exc.messages))
        return Response({"namespace": namespace, "settings": updated})


# --------------------------------------------------------------------------- #
# Workspace rename (username + URL change with 301 aliases)
# --------------------------------------------------------------------------- #
class WorkspaceRenameView(APIView):
    permission_classes = [IsAuthenticated, IsOwner]
    throttle_scope = "workspace"

    def post(self, request):
        _require_password(request)
        new_username = str(request.data.get("workspace_username") or "")
        try:
            hostel = services.rename_workspace_username(
                request.hostel, new_username, actor=request.user
            )
        except DjangoValidationError as exc:
            raise ValidationError(getattr(exc, "message_dict", None) or list(exc.messages))
        return Response({
            "detail": "Workspace username changed. The old URL now redirects permanently.",
            "workspace": WorkspaceSerializer(hostel).data,
        })


# --------------------------------------------------------------------------- #
# Activity logs (workspace-scoped, filterable)
# --------------------------------------------------------------------------- #
class WorkspaceActivityView(APIView):
    permission_classes = [IsAuthenticated, CanView]

    def get(self, request):
        events = AuditEvent.objects.filter(hostel_id=request.hostel.pk)

        action = (request.query_params.get("action") or "").strip()
        if action:
            events = events.filter(action=action)
        query = (request.query_params.get("q") or "").strip()
        if query:
            events = events.filter(
                Q(message__icontains=query) | Q(entity_type__icontains=query)
                | Q(actor__username__icontains=query)
            )
        try:
            limit = max(1, min(int(request.query_params.get("limit", 50)), 200))
        except (TypeError, ValueError):
            limit = 50

        events = events.select_related("actor").order_by("-created_at")[:limit]
        return Response([
            {
                "id": e.id,
                "action": e.action,
                "entity_type": e.entity_type,
                "message": e.message,
                "actor": getattr(e.actor, "username", None),
                "ip_address": e.ip_address,
                "user_agent": (e.user_agent or "")[:120],
                "created_at": e.created_at,
                "meta": e.meta,
            }
            for e in events
        ])


# --------------------------------------------------------------------------- #
# Team management
# --------------------------------------------------------------------------- #
INVITABLE_ROLES = {
    "ADMIN", "MANAGER", "RECEPTIONIST", "ACCOUNTANT", "WARDEN", "STAFF",
    "READ_ONLY", "STUDENT", "PARENT",
}


class TeamView(APIView):
    permission_classes = [IsAuthenticated, CanInvite]

    def get(self, request):
        from apps.accounts.models import UserHostel

        links = (
            UserHostel.objects.filter(hostel=request.hostel)
            .select_related("user")
            .order_by("-created_at")
        )
        return Response([
            {
                "user_id": link.user.id,
                "username": link.user.username,
                "email": link.user.email,
                "name": f"{link.user.first_name} {link.user.last_name}".strip(),
                "role": link.user.role,
                "is_active": link.is_active and link.user.is_active,
                "is_owner": request.hostel.owner_id == link.user.id,
                "last_login": link.user.last_login,
                "joined_at": link.created_at,
            }
            for link in links
        ])

    @transaction.atomic
    def post(self, request):
        """Invite a team member: creates the account in THIS workspace with a
        one-time temporary password (returned to the inviter and emailed
        best-effort). The invitee should change it after first login."""
        from apps.accounts.models import User, UserHostel

        username = str(request.data.get("username") or "").strip()
        email = str(request.data.get("email") or "").strip()
        role = str(request.data.get("role") or "").strip().upper()

        if not username:
            raise ValidationError({"username": "Username is required."})
        if role not in INVITABLE_ROLES:
            raise ValidationError({"role": f"Role must be one of: {', '.join(sorted(INVITABLE_ROLES))}."})
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError({"username": "This username is already taken."})
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError({"email": "This email is already in use."})

        temp_password = secrets.token_urlsafe(9)
        user = User(username=username, email=email, role=role)
        user.set_password(temp_password)
        user.save()
        UserHostel.objects.create(user=user, hostel=request.hostel, is_active=True)

        record_event(request, action=AuditEvent.Action.CREATE, actor=request.user,
                     hostel=request.hostel, message=f"Team member invited ({role})",
                     meta={"invited_user": username, "role": role})

        if email:
            try:
                from django.core.mail import send_mail

                from .branding import email_branding

                brand = email_branding(request.hostel)
                send_mail(
                    # Tenant-branded (white-label aware): the hostel's own
                    # platform name and URL, never the SaaS brand.
                    subject=f"You've been invited to {brand['sender_name']}",
                    message=(
                        f"Hello {username},\n\n"
                        f"You've been added to {brand['sender_name']}.\n\n"
                        f"Sign in: {brand['site_url']}\n"
                        f"Hostel ID: {request.hostel.code}\n"
                        f"Username: {username}\n"
                        f"Temporary password: {temp_password}\n\n"
                        "Please sign in and change your password immediately.\n\n"
                        f"{brand['footer_text']}"
                    ),
                    from_email=brand["from_email"],
                    recipient_list=[email],
                    fail_silently=True,
                )
            except Exception:
                pass

        return Response({
            "detail": "Team member invited.",
            "username": username,
            "role": role,
            # Shown once to the inviter; also emailed when an address was given.
            "temporary_password": temp_password,
        }, status=status.HTTP_201_CREATED)


class TeamMemberView(APIView):
    permission_classes = [IsAuthenticated, CanInvite]

    def _link_for(self, request, user_id):
        from apps.accounts.models import UserHostel

        link = (
            UserHostel.objects.filter(hostel=request.hostel, user_id=user_id)
            .select_related("user")
            .first()
        )
        if link is None:
            raise ValidationError({"detail": "That user is not a member of this workspace."})
        return link

    def patch(self, request, user_id: int):
        """Change a member's role. The workspace owner's role is untouchable,
        and nobody edits their own role (no self-escalation)."""
        link = self._link_for(request, user_id)
        if link.user.id == request.user.id:
            raise ValidationError({"detail": "You cannot change your own role."})
        if request.hostel.owner_id == link.user.id or link.user.role == "OWNER":
            raise ValidationError({"detail": "The workspace owner's role cannot be changed here."})

        role = str(request.data.get("role") or "").strip().upper()
        if role not in INVITABLE_ROLES:
            raise ValidationError({"role": "Invalid role."})
        old_role = link.user.role
        link.user.role = role
        link.user.save(update_fields=["role"])
        record_event(request, action=AuditEvent.Action.UPDATE, actor=request.user,
                     hostel=request.hostel, message="Team member role changed",
                     meta={"user": link.user.username, "from": old_role, "to": role})
        return Response({"detail": "Role updated.", "role": role})

    def delete(self, request, user_id: int):
        """Remove a member from THIS workspace (membership only — the account
        and its data survive; other workspace memberships are untouched)."""
        link = self._link_for(request, user_id)
        if link.user.id == request.user.id:
            raise ValidationError({"detail": "You cannot remove yourself."})
        if request.hostel.owner_id == link.user.id:
            raise ValidationError({"detail": "The workspace owner cannot be removed."})
        username = link.user.username
        link.delete()  # membership-cache invalidation is wired to this signal
        record_event(request, action=AuditEvent.Action.DELETE, actor=request.user,
                     hostel=request.hostel, message="Team member removed",
                     meta={"user": username})
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------- #
# Danger zone (owner + password)
# --------------------------------------------------------------------------- #
class DangerZoneView(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    ACTIONS = {"reset_branding", "reset_theme", "disable_website", "archive", "request_deletion"}

    def post(self, request, action: str):
        if action not in self.ACTIONS:
            return Response({"detail": "Unknown action."}, status=status.HTTP_404_NOT_FOUND)
        _require_password(request)
        hostel = request.hostel

        if action == "reset_branding":
            workspace_settings.reset_workspace_settings(hostel, "branding", actor=request.user)
            detail = "Workspace branding reset to defaults."
        elif action == "reset_theme":
            from apps.website import services as website_services

            website = website_services.get_or_scaffold_website(hostel)
            website.theme = {}
            website.save(update_fields=["theme", "updated_at"])
            detail = "Website theme reset to defaults (publish to apply)."
        elif action == "disable_website":
            from apps.website import services as website_services

            website = website_services.get_or_scaffold_website(hostel)
            website_services.unpublish_website(website, actor=request.user)
            detail = "Public website disabled (unpublished)."
        elif action == "archive":
            services.archive_workspace(hostel, actor=request.user)
            detail = "Workspace archived. It is no longer reachable."
        else:  # request_deletion
            services.soft_delete_workspace(hostel, actor=request.user)
            detail = ("Workspace deletion requested (soft delete). Data is preserved "
                      "and the workspace can be restored by support.")

        record_event(request, action=AuditEvent.Action.UPDATE, actor=request.user,
                     hostel=hostel, message=f"Danger zone: {action}")
        return Response({"detail": detail})


class WorkspaceSettingsExportView(APIView):
    """Danger zone: export/import every workspace-settings namespace as JSON."""

    permission_classes = [IsAuthenticated, IsOwner]

    def get(self, request):
        data = {
            ns: workspace_settings.get_workspace_settings(request.hostel, ns)
            for ns in workspace_settings.WORKSPACE_SETTING_NAMESPACES
        }
        record_event(request, action=AuditEvent.Action.EXPORT, actor=request.user,
                     hostel=request.hostel, message="Workspace settings exported")
        return Response({
            "workspace_username": request.hostel.slug,
            "exported_at": timezone.now(),
            "settings": data,
        })

    def post(self, request):
        _require_password(request)
        payload = request.data.get("settings")
        if not isinstance(payload, dict):
            raise ValidationError({"settings": "Expected an object of {namespace: settings}."})
        applied = []
        for ns, values in payload.items():
            if ns not in workspace_settings.WORKSPACE_SETTING_NAMESPACES:
                raise ValidationError({ns: "Unknown settings namespace."})
            if not isinstance(values, dict):
                raise ValidationError({ns: "Expected an object."})
            try:
                workspace_settings.update_workspace_settings(
                    request.hostel, ns, values, actor=request.user
                )
            except DjangoValidationError as exc:
                raise ValidationError({ns: getattr(exc, "message_dict", None) or list(exc.messages)})
            applied.append(ns)
        record_event(request, action=AuditEvent.Action.UPDATE, actor=request.user,
                     hostel=request.hostel, message="Workspace settings imported",
                     meta={"namespaces": applied})
        return Response({"detail": f"Imported settings for: {', '.join(applied)}."})
