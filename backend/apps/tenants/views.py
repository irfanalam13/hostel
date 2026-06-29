from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.models import UserHostel
from apps.common.permissions import IsOwner
from .models import Hostel, Plan, Subscription, Testimonial, testimonial_stats
from .serializers import (
    HostelSerializer,
    PlanSerializer,
    PublicPlanSerializer,
    PublicTestimonialSerializer,
    SubscriptionSerializer,
    TestimonialSubmitSerializer,
)


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
        featured = Testimonial.objects.filter(is_approved=True, is_featured=True).order_by(
            "sort_order", "-created_at"
        )
        return Response(
            {
                "testimonials": PublicTestimonialSerializer(featured, many=True).data,
                "stats": testimonial_stats(),
            }
        )

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


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        return (
            Subscription.objects.filter(hostel__in=_hostels_for_user(self.request.user))
            .order_by("-start_date")
        )
