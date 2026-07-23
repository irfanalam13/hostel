"""Embedding providers (provider-agnostic, mirrors app/llm).

Ollama (`nomic-embed-text`) for self-hosted dev; the OpenAI-compatible embedder
covers Gemini (`gemini-embedding-001`), OpenAI, etc. A new backend is a subclass
wired into ``get_embedder`` — nothing upstream (ingest API, retriever) changes.
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
                r = await client.post("/api/embeddings", json={"model": self.model, "prompt": t})
                r.raise_for_status()
                out.append(r.json().get("embedding", []))
            return out


class OpenAICompatEmbedding(EmbeddingProvider):
    name = "openai"

    def __init__(self, model: str, base_url: str, api_key: str):
        super().__init__(model=model)
        self.base_url = base_url
        self.api_key = api_key

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=None) as client:
            r = await client.post(
                "/embeddings", json={"model": self.model, "input": texts}, headers=headers
            )
            r.raise_for_status()
            data = r.json().get("data", [])
            # Preserve request order.
            data.sort(key=lambda d: d.get("index", 0))
            return [d.get("embedding", []) for d in data]


def get_embedder() -> EmbeddingProvider:
    if settings.PROVIDER == "ollama":
        return OllamaEmbedding(model=settings.EMBED_MODEL)
    conf = settings.openai_compat
    return OpenAICompatEmbedding(
        model=settings.EMBED_MODEL, base_url=conf["base_url"], api_key=conf["api_key"]
    )
