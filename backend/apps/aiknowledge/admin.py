from django.contrib import admin

from .models import DocumentChunk, KnowledgeDocument


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "hostel", "source_type", "status", "chunk_count", "visibility", "created_at")
    list_filter = ("status", "source_type", "visibility")
    search_fields = ("title",)


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "ordinal", "token_count", "hostel")
    list_filter = ("hostel",)
