"""Ingestion pipeline (Celery).

Extract text → have the ML service chunk + embed it → persist chunks. Runs off
the request path; the document's ``status`` reflects progress so the UI can poll.
"""
from celery import shared_task


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def ingest_document(self, document_id: str):
    from django.db import transaction

    from .extraction import extract_text
    from .models import DocumentChunk, KnowledgeDocument
    from .service_client import MlServiceError, ingest_text

    try:
        doc = KnowledgeDocument.objects.get(pk=document_id)
    except KnowledgeDocument.DoesNotExist:
        return

    KnowledgeDocument.objects.filter(pk=doc.pk).update(
        status=KnowledgeDocument.Status.INGESTING, error=""
    )

    text = extract_text(doc)
    if not text:
        KnowledgeDocument.objects.filter(pk=doc.pk).update(
            status=KnowledgeDocument.Status.FAILED,
            error="No extractable text found in the document.",
        )
        return

    try:
        result = ingest_text(doc.hostel, text)
    except MlServiceError as exc:
        # Retry a couple of times (service warming up / transient), then fail.
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            KnowledgeDocument.objects.filter(pk=doc.pk).update(
                status=KnowledgeDocument.Status.FAILED, error=str(exc)
            )
            return

    chunks = result.get("chunks") or []
    model = result.get("model", "")

    with transaction.atomic():
        DocumentChunk.objects.filter(document=doc).delete()
        DocumentChunk.objects.bulk_create(
            [
                DocumentChunk(
                    hostel=doc.hostel,
                    document=doc,
                    ordinal=c.get("ordinal", i),
                    content=c.get("content", ""),
                    embedding=c.get("embedding", []),
                    token_count=c.get("token_count", 0),
                )
                for i, c in enumerate(chunks)
            ]
        )
        KnowledgeDocument.objects.filter(pk=doc.pk).update(
            status=KnowledgeDocument.Status.READY,
            chunk_count=len(chunks),
            embedding_model=model,
            content=text[:20000],  # keep a bounded cache of the source text
            error="",
        )
