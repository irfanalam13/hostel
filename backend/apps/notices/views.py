from django.utils import timezone
from rest_framework import viewsets

from apps.common.permissions import HasHostelContext, IsStaffOrReadOnly
from .models import Notice
from .serializers import NoticeSerializer


class NoticeViewSet(viewsets.ModelViewSet):
    queryset = Notice.objects.select_related("created_by").all()
    serializer_class = NoticeSerializer
    permission_classes = [HasHostelContext, IsStaffOrReadOnly]
    filterset_fields = ["target_type", "target_value", "is_pinned"]
    search_fields = ["title", "body", "target_value"]
    ordering_fields = ["published_at", "created_at", "is_pinned"]

    def get_queryset(self):
        return self.queryset.filter(hostel=self.request.hostel).filter(
            models_q_expires()
        )

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel, created_by=self.request.user)


def models_q_expires():
    from django.db.models import Q

    return Q(expires_at__isnull=True) | Q(expires_at__gte=timezone.now())
