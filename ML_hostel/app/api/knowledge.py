"""Ingestion + embedding endpoints (Phase 2 RAG).

Called by Django's ingestion Celery task (system context token). This service
chunks + embeds; Django persists the returned chunks. No data is stored here.
"""
from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..config import settings
from ..rag.chunking import chunk_text
from ..rag.embeddings import get_embedder
from ..security import InvalidContext, decode_context

router = APIRouter()


class IngestBody(BaseModel):
    text: str
    title: str | None = None


class EmbedBody(BaseModel):
    input: list[str]


def _auth(authorization: str | None) -> JSONResponse | None:
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse({"detail": "missing token"}, status_code=401)
    try:
        decode_context(authorization[7:].strip())
    except InvalidContext as exc:
        return JSONResponse({"detail": str(exc)}, status_code=401)
    return None


@router.post("/v1/ingest")
async def ingest(body: IngestBody, request: Request, authorization: str | None = Header(default=None)):
    err = _auth(authorization)
    if err:
        return err

    pieces = chunk_text(body.text)
    if not pieces:
        return {"chunks": [], "model": settings.EMBED_MODEL}

    embedder = get_embedder()
    vectors = await embedder.embed(pieces)

    chunks = [
        {
            "ordinal": i,
            "content": piece,
            "embedding": vectors[i] if i < len(vectors) else [],
            "token_count": len(piece.split()),
        }
        for i, piece in enumerate(pieces)
    ]
    return {"chunks": chunks, "model": settings.EMBED_MODEL, "count": len(chunks)}


@router.post("/v1/embed")
async def embed(body: EmbedBody, authorization: str | None = Header(default=None)):
    err = _auth(authorization)
    if err:
        return err
    vectors = await get_embedder().embed(body.input)
    return {"embeddings": vectors, "model": settings.EMBED_MODEL}
