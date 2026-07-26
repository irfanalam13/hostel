"""Website Builder API.

Admin surface (authenticated, RBAC ``website.*``): settings, sections,
publish/versions, inquiries inbox, media. Everything operates on the draft of
``request.hostel``'s website — tenant isolation is inherited from the auth
stack (workspace-bound tokens + membership).

Public surface (anonymous, tenant-resolved by the middleware): the published
snapshot and the inquiry form. The public endpoint serves ONLY the published
snapshot — drafts can never leak.
"""
import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.common.rbac import RequirePermission

from . import services
from .models import WebsiteInquiry, WebsiteMedia, WebsiteSection
from .sections import SECTION_TYPES, default_content_for
from .serializers import (
    InquiryAdminSerializer,
    MediaSerializer,
    PublicInquirySerializer,
    ReorderSerializer,
    SectionSerializer,
    VersionSerializer,
    WebsiteSettingsSerializer,
)

logger = logging.getLogger(__name__)

CanView = RequirePermission("website.view")
CanEdit = RequirePermission("website.edit")
CanPublish = RequirePermission("website.publish")


def _website_for(request):
    return services.get_or_scaffold_website(request.hostel)


class WebsiteSettingsView(APIView):
    """GET the full draft (settings + sections + registry); PATCH settings blobs."""

    permission_classes = [IsAuthenticated, CanView]

    def get(self, request):
        website = _website_for(request)
        return Response({
            "is_published": website.is_published,
            "published_at": website.published_at,
            "published_version": website.published_version,
            "workspace_url": request.hostel.workspace_url,
            "theme": website.effective_theme(),
            "seo": website.effective_seo(),
            "branding": website.effective_branding(),
            "navigation": website.effective_navigation(),
            "footer": website.effective_footer(),
            "social": website.effective_social(),
            "sections": SectionSerializer(
                website.sections.all().order_by("order", "created_at"), many=True
            ).data,
            # The builder UI renders editors straight from the registry.
            "section_types": {
                t: {"label": cfg["label"], "fields": cfg["fields"],
                    "recommended": bool(cfg.get("recommended"))}
                for t, cfg in SECTION_TYPES.items()
            },
        })

    def patch(self, request):
        if not CanEdit().has_permission(request, self):
            return Response({"detail": "You do not have permission to edit the website."},
                            status=status.HTTP_403_FORBIDDEN)
        website = _website_for(request)
        serializer = WebsiteSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changed = list(serializer.validated_data.keys())
        for key, value in serializer.validated_data.items():
            setattr(website, key, value)
        if changed:
            website.save(update_fields=changed + ["updated_at"])
            record_event(request, action=AuditEvent.Action.UPDATE, actor=request.user,
                         hostel=request.hostel, message="Website settings updated",
                         meta={"fields": changed})
        return self.get(request)


class OverviewView(APIView):
    """Builder dashboard: publish state, missing sections, SEO checks, inquiries."""

    permission_classes = [IsAuthenticated, CanView]

    def get(self, request):
        return Response(services.overview(_website_for(request)))


class SectionViewSet(viewsets.ModelViewSet):
    """CRUD + reorder/duplicate for the draft's sections."""

    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated, CanEdit]

    def get_queryset(self):
        return WebsiteSection.objects.filter(
            website=_website_for(self.request)
        ).order_by("order", "created_at")

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), CanView()]
        return super().get_permissions()

    def perform_create(self, serializer):
        website = _website_for(self.request)
        last = website.sections.order_by("-order").first()
        content = serializer.validated_data.get("content") or default_content_for(
            serializer.validated_data["type"]
        )
        serializer.save(
            website=website,
            order=(last.order + 1) if last else 0,
            content=content,
        )

    @action(detail=False, methods=["post"])
    def reorder(self, request):
        """Persist a full ordering (the drag-and-drop / move-buttons result)."""
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = [str(i) for i in serializer.validated_data["order"]]
        sections = {str(s.id): s for s in self.get_queryset()}
        if set(ids) != set(sections):
            return Response(
                {"detail": "Order must contain every section id exactly once."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for position, section_id in enumerate(ids):
            section = sections[section_id]
            if section.order != position:
                section.order = position
                section.save(update_fields=["order", "updated_at"])
        return Response(SectionSerializer(self.get_queryset(), many=True).data)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        source = self.get_object()
        last = self.get_queryset().order_by("-order").first()
        clone = WebsiteSection.objects.create(
            website=source.website,
            type=source.type,
            order=(last.order + 1) if last else 0,
            is_visible=source.is_visible,
            content=source.content,
        )
        return Response(SectionSerializer(clone).data, status=status.HTTP_201_CREATED)


class PublishView(APIView):
    permission_classes = [IsAuthenticated, CanPublish]

    def post(self, request):
        website = _website_for(request)
        version = services.publish_website(
            website, actor=request.user, note=str(request.data.get("note", ""))
        )
        return Response({"detail": "Website published.", "version": version.number})


class UnpublishView(APIView):
    permission_classes = [IsAuthenticated, CanPublish]

    def post(self, request):
        services.unpublish_website(_website_for(request), actor=request.user)
        return Response({"detail": "Website unpublished — it is now offline."})


class VersionsView(APIView):
    permission_classes = [IsAuthenticated, CanView]

    def get(self, request):
        website = _website_for(request)
        versions = website.versions.all()[:50]
        return Response(VersionSerializer(versions, many=True).data)


class VersionRestoreView(APIView):
    permission_classes = [IsAuthenticated, CanPublish]

    def post(self, request, number: int):
        website = _website_for(request)
        try:
            services.restore_version(website, number, actor=request.user)
        except Exception:
            return Response({"detail": "Version not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            "detail": f"Draft restored from version {number}. Review it, then publish.",
        })


class InquiryViewSet(viewsets.ModelViewSet):
    """Admin inbox for public inquiries (read + status updates + delete)."""

    serializer_class = InquiryAdminSerializer
    permission_classes = [IsAuthenticated, CanView]
    http_method_names = ["get", "patch", "delete"]
    filterset_fields = ["status"]

    def get_queryset(self):
        return WebsiteInquiry.objects.filter(hostel=self.request.hostel)


class MediaViewSet(viewsets.ModelViewSet):
    """Validated website asset uploads (images + PDFs), tenant-scoped."""

    serializer_class = MediaSerializer
    permission_classes = [IsAuthenticated, CanEdit]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return WebsiteMedia.objects.filter(hostel=self.request.hostel)

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), CanView()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel, uploaded_by=self.request.user)
        record_event(self.request, action=AuditEvent.Action.CREATE, actor=self.request.user,
                     hostel=self.request.hostel, message="Website media uploaded")


# --------------------------------------------------------------------------- #
# Public surface
# --------------------------------------------------------------------------- #
class PublicWebsiteView(APIView):
    """The published website for the resolved workspace. Anonymous; the tenant
    middleware already 403/404s suspended/archived workspaces upstream."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        from apps.tenants.workspace_settings import get_workspace_settings

        hostel = getattr(request, "tenant", None) or getattr(request, "hostel", None)
        if hostel is None:
            return Response({"detail": "No workspace resolved for this request."},
                            status=status.HTTP_404_NOT_FOUND)

        # Workspace preferences (Prompt 04): the public-website master switch.
        prefs = get_workspace_settings(hostel, "preferences")
        if not prefs.get("enable_public_website", True):
            return Response(
                {"detail": "This website is not published.",
                 "code": "website_unpublished"},
                status=status.HTTP_404_NOT_FOUND,
            )

        website = services.get_or_scaffold_website(hostel)
        if not website.is_published:
            return Response(
                {"detail": "This website is not published.",
                 "code": "website_unpublished"},
                status=status.HTTP_404_NOT_FOUND,
            )
        payload = services.public_payload(website, hostel)

        # Feature toggles hide whole section types without touching the draft.
        toggle_by_type = {
            "gallery": prefs.get("enable_gallery", True),
            "events": prefs.get("enable_events", True),
            "notices": prefs.get("enable_public_notices", True),
        }
        payload["sections"] = [
            s for s in payload["sections"] if toggle_by_type.get(s.get("type"), True)
        ]
        if not prefs.get("enable_online_inquiry", True):
            for section in payload["sections"]:
                if section.get("type") == "contact":
                    section["content"] = {**section.get("content", {}),
                                          "show_inquiry_form": False}
        return Response(payload)


class PublicInquiryView(APIView):
    """Public inquiry form: throttled per-IP, honeypot-filtered, audited."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "website_inquiry"

    def post(self, request):
        from apps.tenants.workspace_settings import get_workspace_settings

        hostel = getattr(request, "tenant", None) or getattr(request, "hostel", None)
        if hostel is None:
            return Response({"detail": "No workspace resolved for this request."},
                            status=status.HTTP_404_NOT_FOUND)

        # Workspace preference: the inquiry form can be turned off entirely.
        if not get_workspace_settings(hostel, "preferences").get("enable_online_inquiry", True):
            return Response({"detail": "Inquiries are disabled for this website."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = PublicInquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        honeypot = data.pop("website", "")

        response = Response(
            {"detail": "Thanks! We received your inquiry and will get back to you soon."},
            status=status.HTTP_201_CREATED,
        )
        if honeypot:
            # A filled honeypot is a bot: acknowledge (no oracle) but store nothing.
            return response

        inquiry = WebsiteInquiry.objects.create(
            hostel=hostel,
            ip_address=request.META.get("REMOTE_ADDR") or None,
            **data,
        )
        record_event(request, action=AuditEvent.Action.CREATE, hostel=hostel,
                     message="Website inquiry received",
                     meta={"inquiry_id": str(inquiry.id)})
        return response
