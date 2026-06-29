from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .models import Faq, Lead, LegalDocument, SitePage
from .serializers import (
    FaqSerializer,
    LeadSubmitSerializer,
    LegalDocumentSerializer,
    SitePageSerializer,
)


class _PublicViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only, fully public base: no auth, anyone can read."""
    authentication_classes = []
    permission_classes = [AllowAny]


class FaqViewSet(_PublicViewSet):
    queryset = Faq.objects.filter(is_published=True)
    serializer_class = FaqSerializer


class LegalDocumentViewSet(_PublicViewSet):
    queryset = LegalDocument.objects.filter(is_published=True)
    serializer_class = LegalDocumentSerializer
    lookup_field = "slug"


class SitePageViewSet(_PublicViewSet):
    queryset = SitePage.objects.filter(is_published=True)
    serializer_class = SitePageSerializer
    lookup_field = "slug"


class LeadViewSet(viewsets.GenericViewSet):
    """
    Public lead capture for the landing Contact section.

      POST /api/marketing/leads/  -> create a sales/demo enquiry

    Public + throttled. Leads are reviewed by staff in the Django admin.
    """
    queryset = Lead.objects.all()
    serializer_class = LeadSubmitSerializer
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = "lead"

    def get_throttles(self):
        if self.action == "create":
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def create(self, request):
        serializer = LeadSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(source="landing")
        return Response(
            {"detail": "Thanks! Our team will be in touch shortly."},
            status=status.HTTP_201_CREATED,
        )
