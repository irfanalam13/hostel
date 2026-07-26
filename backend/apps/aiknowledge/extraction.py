"""Text extraction for knowledge documents.

Kept in Django (not the AI service): pulling text out of a file is plain
document handling, not model inference. Supports pasted content, plain
text/markdown, and PDF (via pypdf). Unknown binary types fall back to any
provided ``content``.
"""
import io


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        return ""
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception:
        return ""


def extract_text(document) -> str:
    """Best-effort plain text for a KnowledgeDocument."""
    # Pasted text / FAQ / notice content wins if present.
    if document.content and document.content.strip():
        return document.content.strip()

    f = document.file
    if not f:
        return ""

    name = (f.name or "").lower()
    try:
        f.open("rb")
        data = f.read()
    finally:
        try:
            f.close()
        except Exception:
            pass

    if name.endswith(".pdf"):
        return _extract_pdf(data)
    # txt / md / csv / anything utf-8 decodable.
    try:
        return data.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""
