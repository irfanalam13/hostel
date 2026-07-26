"""Chunking tests (no network / no model needed)."""
import os

os.environ.setdefault("ML_SHARED_SECRET", "test-secret")

from app.rag.chunking import chunk_text  # noqa: E402


def test_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_single_chunk():
    assert chunk_text("Just one short paragraph.") == ["Just one short paragraph."]


def test_packs_paragraphs_within_size():
    text = "\n\n".join(["para " + str(i) for i in range(3)])
    chunks = chunk_text(text, size=1000, overlap=0)
    assert len(chunks) == 1


def test_splits_when_over_size():
    paras = ["x" * 100 for _ in range(20)]  # 20 paragraphs of 100 chars
    chunks = chunk_text("\n\n".join(paras), size=300, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 300 * 1.5 for c in chunks)


def test_hard_split_oversized_paragraph():
    chunks = chunk_text("y" * 5000, size=1000, overlap=100)
    assert len(chunks) >= 5
