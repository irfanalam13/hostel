"""Knowledge base CRUD (Phase 2 RAG).

Managing the KB (create/upload/delete) needs ``ai.manage``; viewing needs
``ai.view``. Every write is workspace-scoped and audited, and creating/replacing
a document (re)queues ingestion so embeddings stay in sync with the source.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.common.permissions import IsHostelResolved
from apps.common.rbac import ActionPermissions
from apps.subscriptions.gates import RequiresFeature

from .models import DocumentChunk, KnowledgeDocument
from .serializers import KnowledgeDocumentSerializer
from .tasks import ingest_document


class KnowledgeDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = KnowledgeDocumentSerializer
    permission_classes = [IsHostelResolved, ActionPermissions, RequiresFeature("ai_rag")]
    permission_map = {
        "list": ["ai.view"], "retrieve": ["ai.view"],
        "create": ["ai.manage"], "update": ["ai.manage"],
        "partial_update": ["ai.manage"], "destroy": ["ai.manage"],
        "reingest": ["ai.manage"],
    }
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ["title"]
    filterset_fields = ["status", "source_type", "visibility"]

    def get_queryset(self):
        return KnowledgeDocument.objects.filter(hostel=self.request.hostel)

    def _audit(self, action_, obj, message):
        record_event(
            self.request, action=action_, actor=self.request.user, hostel=self.request.hostel,
            entity_type="ai.knowledgedocument", entity_id=obj.id, message=message,
        )

    def _requeue(self, obj):
        obj.chunks.all().delete()
        KnowledgeDocument.objects.filter(pk=obj.pk).update(
            status=KnowledgeDocument.Status.PENDING, chunk_count=0, error=""
        )
        ingest_document.delay(str(obj.id))

    def perform_create(self, serializer):
        obj = serializer.save(
            hostel=self.request.hostel,
            created_by=self.request.user,
            status=KnowledgeDocument.Status.PENDING,
        )
        self._audit(AuditEvent.Action.CREATE, obj, f"KB document added: {obj.title}")
        ingest_document.delay(str(obj.id))

    def perform_update(self, serializer):
        obj = serializer.save()
        # Source may have changed — drop stale chunks and re-ingest.
        self._requeue(obj)
        self._audit(AuditEvent.Action.UPDATE, obj, f"KB document updated: {obj.title}")

    def perform_destroy(self, instance):
        DocumentChunk.objects.filter(document=instance).delete()
        self._audit(AuditEvent.Action.DELETE, instance, f"KB document removed: {instance.title}")
        instance.delete()

    @action(detail=True, methods=["post"])
    def reingest(self, request, pk=None):
        obj = self.get_object()
        self._requeue(obj)
        return Response({"status": "queued"}, status=status.HTTP_202_ACCEPTED)
