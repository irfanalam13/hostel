from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.common.rbac import RequirePermission
from apps.subscriptions.permissions import IsPlatformAdmin

from .filters import DirectoryHostelFilter
from .models import Review, ReviewFlag
from .permissions import IsReviewAuthor
from .serializers import (
    DirectoryHostelDetailSerializer,
    DirectoryHostelListSerializer,
    MyReviewSerializer,
    ReviewCreateSerializer,
    ReviewFlagCreateSerializer,
    ReviewModerationSerializer,
    ReviewPublicSerializer,
    ReviewResponseCreateSerializer,
    ReviewUpdateSerializer,
)
from .services import visible_hostels_queryset

CanModerate = RequirePermission("discovery.moderate")
CanRespond = RequirePermission("discovery.respond")


class DirectoryHostelViewSet(viewsets.ReadOnlyModelViewSet):
    """Public, anonymous, cross-tenant directory of every listed hostel.

    GET /api/discovery/hostels/                 paginated, filterable list
    GET /api/discovery/hostels/{slug}/           detail
    GET /api/discovery/hostels/{slug}/reviews/   published reviews for one hostel
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    lookup_field = "slug"
    filterset_class = DirectoryHostelFilter
    search_fields = ["name", "discovery_profile__city", "discovery_profile__district"]
    ordering_fields = ["discovery_profile__average_rating", "name", "created_at"]
    ordering = ["-discovery_profile__average_rating", "name"]

    def get_queryset(self):
        return visible_hostels_queryset()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DirectoryHostelDetailSerializer
        return DirectoryHostelListSerializer

    @action(detail=True, methods=["get"])
    def reviews(self, request, slug=None):
        hostel = self.get_object()
        qs = (
            Review.objects.filter(hostel=hostel, status=Review.Status.PUBLISHED)
            .select_related("owner_response")
            .order_by("-created_at")
        )
        page = self.paginate_queryset(qs)
        serializer = ReviewPublicSerializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReviewViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Consumer-facing review CRUD.

    POST   /api/discovery/reviews/            create (runs verification)
    PATCH  /api/discovery/reviews/{id}/        author only
    DELETE /api/discovery/reviews/{id}/        author only (hard delete —
                                                lets a reviewer delete and
                                                resubmit; the (hostel, author)
                                                uniqueness only guards against
                                                duplicate LIVE reviews)
    POST   /api/discovery/reviews/{id}/flag/   report a review
    POST   /api/discovery/reviews/{id}/respond/  hostel staff reply
    """

    queryset = Review.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return ReviewCreateSerializer
        if self.action in ("update", "partial_update"):
            return ReviewUpdateSerializer
        if self.action == "flag":
            return ReviewFlagCreateSerializer
        if self.action == "respond":
            return ReviewResponseCreateSerializer
        return ReviewPublicSerializer

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsReviewAuthor()]
        if self.action == "respond":
            return [IsAuthenticated(), CanRespond()]
        return [IsAuthenticated()]

    # Read by the project-wide ResilientScopedRateThrottle (part of
    # DEFAULT_THROTTLE_CLASSES) — not a custom get_throttles()/throttle_classes
    # override, so the test suite's throttle-disabling (settings_test.py) still
    # applies here exactly like every other view.
    @property
    def throttle_scope(self):
        return {"create": "discovery_review", "flag": "discovery_flag"}.get(self.action, "")

    @action(detail=False, methods=["get"])
    def mine(self, request):
        """The current consumer's own review for one hostel (any status —
        pending/published/rejected/flagged), or null if they haven't reviewed
        it yet. Lets the frontend decide between a create form and an
        edit/delete view without a separate eligibility pre-check."""
        hostel_slug = request.query_params.get("hostel", "")
        if not hostel_slug:
            return Response({"detail": "hostel query param is required."}, status=status.HTTP_400_BAD_REQUEST)
        review = Review.objects.filter(hostel__slug=hostel_slug, author=request.user).first()
        if review is None:
            return Response({"detail": "No review yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response(MyReviewSerializer(review).data)

    @action(detail=True, methods=["post"])
    def flag(self, request, pk=None):
        review = self.get_object()
        serializer = ReviewFlagCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(review=review, reporter=request.user)

        threshold = 3
        review.flag_count = review.flags.filter(status=ReviewFlag.Status.OPEN).count()
        update_fields = ["flag_count"]
        if review.flag_count >= threshold and review.status == Review.Status.PUBLISHED:
            review.status = Review.Status.FLAGGED
            update_fields.append("status")
        review.save(update_fields=update_fields)
        return Response(
            {"detail": "Thanks — this review has been reported for moderation."},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        from .models import ReviewResponse

        review = self.get_object()
        hostel = getattr(request, "hostel", None)
        if hostel is None or review.hostel_id != hostel.id:
            return Response(
                {"detail": "This review does not belong to your workspace."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ReviewResponseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response, _ = ReviewResponse.objects.update_or_create(
            review=review,
            defaults={**serializer.validated_data, "responded_by": request.user},
        )
        return Response(ReviewResponseCreateSerializer(response).data, status=status.HTTP_200_OK)


class ModerationPendingView(APIView):
    """Tenant-staff inbox of reviews awaiting manual verification (phone
    match failed or was ambiguous at submission time)."""

    permission_classes = [IsAuthenticated, CanModerate]

    def get(self, request):
        hostel = getattr(request, "hostel", None)
        if hostel is None:
            return Response(
                {"detail": "No workspace resolved for this request."},
                status=status.HTTP_404_NOT_FOUND,
            )
        qs = Review.objects.filter(hostel=hostel, status=Review.Status.PENDING).order_by("-created_at")
        return Response(ReviewModerationSerializer(qs, many=True).data)


class ModerationApproveView(APIView):
    permission_classes = [IsAuthenticated, CanModerate]

    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk, hostel=request.hostel, status=Review.Status.PENDING)
        review.status = Review.Status.PUBLISHED
        review.verification_method = Review.VerificationMethod.STAFF_APPROVED
        review.verified_at = timezone.now()
        review.verified_by = request.user
        review.save()
        return Response(ReviewModerationSerializer(review).data)


class ModerationRejectView(APIView):
    permission_classes = [IsAuthenticated, CanModerate]

    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk, hostel=request.hostel, status=Review.Status.PENDING)
        review.status = Review.Status.REJECTED
        review.save(update_fields=["status", "updated_at"])
        return Response(ReviewModerationSerializer(review).data)


class PlatformFlaggedQueueView(APIView):
    """Cross-tenant queue of reviews auto-flagged past the report threshold."""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        qs = (
            Review.objects.filter(status=Review.Status.FLAGGED)
            .select_related("hostel")
            .order_by("-updated_at")
        )
        return Response(ReviewModerationSerializer(qs, many=True).data)


class PlatformReviewUnflagView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk, status=Review.Status.FLAGGED)
        review.status = Review.Status.PUBLISHED
        review.flags.filter(status=ReviewFlag.Status.OPEN).update(status=ReviewFlag.Status.DISMISSED)
        review.flag_count = 0
        review.save(update_fields=["status", "flag_count", "updated_at"])
        record_event(
            request, action=AuditEvent.Action.UPDATE, entity_type="review",
            entity_id=str(review.pk), message="review unflagged", hostel=review.hostel,
        )
        return Response(ReviewModerationSerializer(review).data)


class PlatformReviewRemoveView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        review.flags.filter(status=ReviewFlag.Status.OPEN).update(status=ReviewFlag.Status.ACTIONED)
        review.status = Review.Status.REMOVED
        review.save(update_fields=["status", "updated_at"])
        record_event(
            request, action=AuditEvent.Action.DELETE, entity_type="review",
            entity_id=str(review.pk), message="review removed", hostel=review.hostel,
        )
        return Response(ReviewModerationSerializer(review).data)
