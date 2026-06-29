from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import UserHostel
from apps.common.permissions import IsOwner
from .models import Hostel, Plan, Subscription
from .serializers import (
    HostelSerializer,
    PlanSerializer,
    PublicPlanSerializer,
    SubscriptionSerializer,
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
