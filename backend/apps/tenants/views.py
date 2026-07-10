import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.models import UserHostel
from apps.common.permissions import IsOwner
from . import services
from .models import Hostel, Plan, Subscription, Testimonial, testimonial_stats
from .serializers import (
    HostelSerializer,
    PlanSerializer,
    PublicPlanSerializer,
    PublicTestimonialSerializer,
    SubscriptionSerializer,
    TestimonialSubmitSerializer,
    WorkspaceRegisterSerializer,
    WorkspaceSerializer,
)
from .validators import clean_workspace_username, normalize_workspace_username


logger = logging.getLogger(__name__)


def _hostels_for_user(user):
    if user.is_superuser:
        return Hostel.objects.all()
    return Hostel.objects.filter(user_links__user=user, user_links__is_active=True).distinct()


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """Subscription plans are global, read-only catalog data — auth required."""
    queryset = Plan.objects.all().order_by("sort_order", "price_monthly", "name")
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def public(self, request):
        """
        Unauthenticated catalog for the marketing landing page: only plans
        flagged public, with display-ready pricing + live discount applied.
        """
        plans = Plan.objects.filter(is_public=True).order_by(
            "sort_order", "price_monthly", "name"
        )
        return Response(PublicPlanSerializer(plans, many=True).data)


class TestimonialViewSet(viewsets.GenericViewSet):
    """
    Public reviews for the landing page.

      GET  /api/tenants/testimonials/   -> featured reviews + aggregate stats
      POST /api/tenants/testimonials/   -> submit a review (lands unapproved)

    Fully public: no authentication, so anonymous landing visitors can read and
    submit. Submissions are throttled and start unapproved/unfeatured — an admin
    curates them before anything shows.
    """
    queryset = Testimonial.objects.all()
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "review"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def list(self, request):
        try:
            featured = Testimonial.objects.filter(is_approved=True, is_featured=True).order_by(
                "sort_order", "-created_at"
            )
            data = {
                "testimonials": PublicTestimonialSerializer(featured, many=True).data,
                "stats": testimonial_stats(),
            }
        except Exception:
            # This is a public landing-page endpoint: a transient DB issue or a
            # not-yet-applied migration must degrade to "no featured reviews"
            # (the frontend then shows its static copy) rather than 500 the page.
            logger.exception("testimonials list failed; serving empty payload")
            data = {"testimonials": [], "stats": None}
        return Response(data)

    def create(self, request):
        serializer = TestimonialSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Force moderation defaults regardless of what the client sends.
        serializer.save(is_approved=False, is_featured=False, source="web")
        return Response(
            {"detail": "Thanks for your review! It will appear once approved."},
            status=status.HTTP_201_CREATED,
        )


class HostelViewSet(viewsets.ModelViewSet):
    serializer_class = HostelSerializer
    # Reads scoped to the caller's hostels; writes restricted to owner/admin.
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _hostels_for_user(self.request.user).order_by("-created_at")

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsOwner()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        hostel = serializer.save()
        # Link the creating user so they retain access to the new hostel.
        UserHostel.objects.get_or_create(
            user=self.request.user, hostel=hostel, defaults={"is_active": True}
        )


class WorkspaceViewSet(viewsets.GenericViewSet):
    """Workspace (tenant) management.

      GET    /api/tenants/workspaces/availability/  -> username availability (public)
      POST   /api/tenants/workspaces/               -> register a workspace
      GET    /api/tenants/workspaces/               -> my workspaces
      GET    /api/tenants/workspaces/current/       -> the resolved workspace
      GET    /api/tenants/workspaces/{id}/          -> workspace detail (member)
      PATCH  /api/tenants/workspaces/{id}/          -> update display fields (owner)
      DELETE /api/tenants/workspaces/{id}/          -> soft delete (owner)
      POST   /api/tenants/workspaces/{id}/suspend|archive|restore/  (owner)

    The workspace username (slug) is permanent and never editable.
    """

    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Soft-deleted workspaces stay out of every listing/detail.
        return _hostels_for_user(self.request.user).filter(is_deleted=False).order_by("-created_at")

    def get_throttles(self):
        # ScopedRateThrottle is in DEFAULT_THROTTLE_CLASSES; it applies only
        # to actions that set a scope here.
        if self.action == "availability":
            self.throttle_scope = "workspace_check"
        elif self.action == "create":
            self.throttle_scope = "workspace"
        return super().get_throttles()

    def get_permissions(self):
        if self.action in ("availability", "public"):
            return [AllowAny()]
        if self.action in ("partial_update", "update", "destroy",
                           "suspend", "archive", "restore"):
            return [IsAuthenticated(), IsOwner()]
        return [IsAuthenticated()]

    # ------------------------------------------------------------------ #
    # Public workspace branding (login pages)
    # ------------------------------------------------------------------ #
    @action(detail=False, methods=["get"], authentication_classes=[],
            permission_classes=[AllowAny])
    def public(self, request):
        """Safe, unauthenticated branding for the resolved workspace's login
        pages: name, workspace username, logo, locale. Requires workspace
        context (subdomain / X-Workspace) — 404 otherwise. Deliberately never
        exposes owner, contact, plan or settings data."""
        tenant = getattr(request, "tenant", None) or getattr(request, "hostel", None)
        if tenant is None:
            return Response(
                {"detail": "No workspace resolved for this request."},
                status=status.HTTP_404_NOT_FOUND,
            )
        # Workspace branding (Prompt 04) wins over the raw logo file — this is
        # how branding propagates to login pages and portals automatically.
        from .workspace_settings import get_workspace_settings

        branding = get_workspace_settings(tenant, "branding")
        logo_url = branding.get("logo") or ""
        if not logo_url:
            try:
                if tenant.logo:
                    logo_url = request.build_absolute_uri(tenant.logo.url)
            except Exception:
                logo_url = ""
        # White-label (Prompt 05): login pages/portals title themselves as the
        # hostel's own system when configured.
        from .branding import public_url as tenant_public_url, white_label

        wl = white_label(tenant)
        return Response({
            "name": tenant.name,
            "workspace_username": tenant.slug,
            "workspace_url": tenant.workspace_url,
            "public_url": tenant_public_url(tenant),
            "status": tenant.status,
            "logo": logo_url,
            "dark_logo": branding.get("dark_logo") or "",
            "login_background": branding.get("login_background") or "",
            "language": tenant.language,
            "currency": tenant.currency,
            "timezone": tenant.timezone,
            "white_label": {
                "enabled": bool(wl.get("enabled")),
                "platform_name": wl["platform_name"],
                "browser_title": wl["browser_title"],
                "footer_text": wl.get("footer_text") or "",
                "hide_platform_branding": bool(wl.get("hide_platform_branding")),
            },
        })

    # ------------------------------------------------------------------ #
    # Public availability checker
    # ------------------------------------------------------------------ #
    @action(detail=False, methods=["get"], authentication_classes=[])
    def availability(self, request):
        """Real-time workspace-username availability + suggestions."""
        raw = request.query_params.get("username", "")
        normalized = normalize_workspace_username(raw)
        try:
            clean_workspace_username(raw)
        except DjangoValidationError as exc:
            return Response({
                "username": normalized,
                "available": False,
                "reason": getattr(exc, "code", None) or "invalid",
                "detail": "; ".join(exc.messages),
                "suggestions": services.suggest_workspace_usernames(normalized),
            })

        available = services.is_workspace_username_available(normalized)
        return Response({
            "username": normalized,
            "available": available,
            "reason": None if available else "taken",
            "detail": "" if available else "This workspace username is already taken.",
            "suggestions": [] if available else services.suggest_workspace_usernames(normalized),
        })

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    def list(self, request):
        page = self.paginate_queryset(self.get_queryset())
        serializer = self.get_serializer(page or self.get_queryset(), many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)

    def create(self, request):
        serializer = WorkspaceRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            hostel = services.provision_workspace(
                owner=request.user,
                hostel_name=data["hostel_name"],
                workspace_username=data.get("workspace_username") or None,
                phone=data.get("phone", ""),
                address=data.get("address", ""),
                timezone_name=data.get("timezone", ""),
                currency=data.get("currency", ""),
                language=data.get("language", ""),
            )
        except DjangoValidationError as exc:
            raise ValidationError(getattr(exc, "message_dict", None) or list(exc.messages))
        return Response(WorkspaceSerializer(hostel).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        services.soft_delete_workspace(self.get_object(), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------ #
    # Context + lifecycle
    # ------------------------------------------------------------------ #
    @action(detail=False, methods=["get"])
    def current(self, request):
        """The workspace resolved for this request (subdomain / headers / token)."""
        hostel = getattr(request, "tenant", None) or getattr(request, "hostel", None)
        if hostel is None:
            return Response(
                {"detail": "No workspace resolved for this request."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not self.get_queryset().filter(pk=hostel.pk).exists():
            return Response(
                {"detail": "You are not a member of this workspace."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(WorkspaceSerializer(hostel).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        hostel = services.suspend_workspace(
            self.get_object(), actor=request.user,
            reason=str(request.data.get("reason", ""))[:255],
        )
        return Response(WorkspaceSerializer(hostel).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        hostel = services.archive_workspace(self.get_object(), actor=request.user)
        return Response(WorkspaceSerializer(hostel).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        # Restore must be able to see archived + soft-deleted workspaces.
        hostel = (
            _hostels_for_user(request.user).filter(pk=pk).first()
        )
        if hostel is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        hostel = services.restore_workspace(hostel, actor=request.user)
        return Response(WorkspaceSerializer(hostel).data)


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        return (
            Subscription.objects.filter(hostel__in=_hostels_for_user(self.request.user))
            .order_by("-start_date")
        )
