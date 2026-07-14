"""Embedding providers (provider-agnostic, mirrors app/llm).

Default is Ollama (`nomic-embed-text`). A new backend is a subclass wired into
``get_embedder`` — nothing upstream (ingest API, retriever) changes.
"""
from __future__ import annotations

import httpx

from ..config import settings


class EmbeddingProvider:
    name = "base"

    def __init__(self, model: str):
        self.model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        raise NotImplementedError


class OllamaEmbedding(EmbeddingProvider):
    name = "ollama"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        async with httpx.AsyncClient(base_url=settings.OLLAMA_URL, timeout=None) as client:
            # Prefer the batch /api/embed; fall back to per-text /api/embeddings
            # for older Ollama builds.
            try:
                r = await client.post("/api/embed", json={"model": self.model, "input": texts})
                r.raise_for_status()
                data = r.json()
                if "embeddings" in data:
                    return data["embeddings"]
            except httpx.HTTPStatusError:
                pass

            out: list[list[float]] = []
            for t in texts:
                r = await client.post(
                    "/api/embeddings", json={"model": self.model, "prompt": t}
                )
                r.raise_for_status()
                out.append(r.json().get("embedding", []))
            return out


def get_embedder() -> EmbeddingProvider:
    # Embeddings currently always run on Ollama (cheap, local, good quality).
    # To add a dedicated embedding backend (e.g. OpenAI text-embedding-3), branch
    # on an ML_EMBED_PROVIDER env here and return the subclass — callers are blind
    # to the choice.
    return OllamaEmbedding(model=settings.EMBED_MODEL)
