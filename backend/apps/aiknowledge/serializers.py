from rest_framework import serializers

from .models import KnowledgeDocument


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeDocument
        fields = [
            "id", "title", "source_type", "file", "content", "visibility",
            "status", "error", "chunk_count", "embedding_model", "created_at",
        ]
        read_only_fields = ["status", "error", "chunk_count", "embedding_model", "created_at"]

    def validate(self, attrs):
        # A document needs either an uploaded file or pasted content to ingest.
        source = attrs.get("source_type", getattr(self.instance, "source_type", "UPLOAD"))
        has_file = bool(attrs.get("file") or getattr(self.instance, "file", None))
        has_content = bool((attrs.get("content") or getattr(self.instance, "content", "")).strip())
        if source == KnowledgeDocument.Source.UPLOAD and not has_file and not has_content:
            raise serializers.ValidationError("Upload a file or provide text content.")
        if source in (KnowledgeDocument.Source.TEXT, KnowledgeDocument.Source.FAQ) and not has_content:
            raise serializers.ValidationError("content is required for text/FAQ documents.")
        return attrs
