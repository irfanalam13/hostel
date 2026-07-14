"""Text chunking for RAG ingestion.

Paragraph-aware, character-budgeted chunks with a small overlap so a passage
that straddles a boundary still surfaces. Deliberately simple and dependency-free
— good enough for policy/manual/FAQ documents; swap for a token-aware splitter
later without touching callers.
"""
from ..config import settings


def chunk_text(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    size = size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP
    text = (text or "").strip()
    if not text:
        return []

    # Split on blank lines into paragraphs, then greedily pack into chunks.
    paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if not current:
            current = para
        elif len(current) + len(para) + 2 <= size:
            current += "\n\n" + para
        else:
            chunks.append(current)
            # carry an overlap tail from the previous chunk for continuity
            tail = current[-overlap:] if overlap else ""
            current = (tail + "\n\n" + para).strip() if tail else para

    if current:
        chunks.append(current)

    # Hard-split any oversized single paragraph.
    final: list[str] = []
    for c in chunks:
        if len(c) <= size * 1.5:
            final.append(c)
        else:
            step = size - overlap
            for i in range(0, len(c), step if step > 0 else size):
                final.append(c[i : i + size])
    return final
