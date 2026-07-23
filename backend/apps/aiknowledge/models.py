"""Knowledge base for RAG (Phase 2).

Documents (uploaded files or pasted text) are chunked and embedded so the AI
assistant can ground answers in a workspace's own policies/manuals/FAQs with
citations. Everything is workspace-scoped (`HostelScopedModel`), and retrieval is
permission-aware via ``visibility``.

Embeddings are stored as an in-DB JSON vector and searched with brute-force
cosine similarity in ``apps.assistant.tools``. This is intentional: a per-tenant
KB is small (dozens–hundreds of chunks), so this is fast and needs no infra
change (dev runs on host Postgres; prod on managed Postgres — neither has
pgvector). The retriever is isolated behind one function, so pgvector (or an
external vector DB) is a drop-in for scale later.
"""
from django.conf import settings
from django.db import models

from apps.common.models import HostelScopedModel


def knowledge_upload_path(instance, filename):
    return f"ai_knowledge/{instance.hostel_id}/{filename}"


class KnowledgeDocument(HostelScopedModel):
    class Source(models.TextChoices):
        UPLOAD = "UPLOAD", "Uploaded file"
        TEXT = "TEXT", "Pasted text"
        NOTICE = "NOTICE", "Notice"
        FAQ = "FAQ", "FAQ"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        INGESTING = "INGESTING", "Ingesting"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Failed"

    class Visibility(models.TextChoices):
        # STAFF: any staff member of the workspace may retrieve it.
        STAFF = "STAFF", "All staff"
        # ADMIN: only owners/admins (or ai.manage holders) may retrieve it.
        ADMIN = "ADMIN", "Admins only"

    title = models.CharField(max_length=200)
    source_type = models.CharField(max_length=12, choices=Source.choices, default=Source.UPLOAD)
    file = models.FileField(upload_to=knowledge_upload_path, null=True, blank=True)
    # Pasted text, or a cache of the text extracted from the file.
    content = models.TextField(blank=True)
    visibility = models.CharField(max_length=8, choices=Visibility.choices, default=Visibility.STAFF)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    error = models.TextField(blank=True)
    chunk_count = models.PositiveIntegerField(default=0)
    embedding_model = models.CharField(max_length=80, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="ai_documents",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["hostel", "status"])]

    def __str__(self):
        return self.title


class DocumentChunk(HostelScopedModel):
    document = models.ForeignKey(
        KnowledgeDocument, on_delete=models.CASCADE, related_name="chunks"
    )
    ordinal = models.PositiveIntegerField(default=0)
    content = models.TextField()
    # The embedding vector as a JSON list[float]. See module docstring.
    embedding = models.JSONField(default=list)
    token_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["document", "ordinal"]
        indexes = [models.Index(fields=["hostel", "document"])]
