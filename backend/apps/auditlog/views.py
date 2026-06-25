from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.common.permissions import IsOwnerOrManager
from .models import AuditEvent
from .serializers import AuditEventSerializer

class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditEvent.objects.all().order_by("-created_at")
    serializer_class = AuditEventSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManager]